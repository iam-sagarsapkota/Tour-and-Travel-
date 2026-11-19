"""Payment gateway adapters.

Each adapter turns a ``PaymentAttempt`` into a browser redirect and later asks the
provider, server to server, what really happened. The browser redirect back to
our site is never trusted on its own.

eSewa ePay v2: https://developer.esewa.com.np/pages/Epay
Khalti KPG-2:  https://docs.khalti.com/khalti-epayment/
"""

import base64
import binascii
import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .models import PaymentAttempt, Provider

Status = PaymentAttempt.Status


class GatewayError(Exception):
    """The provider could not be reached or answered with something unusable."""


@dataclass
class Redirect:
    """How the browser should leave for the gateway."""

    method: str  # "GET" or "POST"
    url: str
    fields: dict[str, str] = field(default_factory=dict)
    token: str = ""  # provider id to remember (Khalti pidx)
    raw: dict = field(default_factory=dict)


@dataclass
class Result:
    """The provider's server-side answer about an attempt."""

    status: str  # a PaymentAttempt.Status value
    gateway_status: str
    amount: Decimal | None
    transaction_id: str = ""
    raw: dict = field(default_factory=dict)


def http_json(method: str, url: str, *, params=None, body=None, headers=None) -> tuple[int, dict]:
    """Small JSON-over-HTTPS client. Returns (status, json) even for 4xx answers."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(  # noqa: S310 - URLs come from settings, always https
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.PAYMENT_HTTP_TIMEOUT) as response:  # noqa: S310
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError as parse_error:
            raise GatewayError(f"HTTP {exc.code} from provider") from parse_error
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise GatewayError(str(exc)) from exc


def _decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation, TypeError:
        return None


def format_amount(amount: Decimal) -> str:
    """'38000.00' -> '38000', '19999.50' -> '19999.5' (plain notation, never exponent)."""
    text = format(amount.quantize(Decimal("0.01")), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


# --- eSewa ---------------------------------------------------------------------


class EsewaGateway:
    code = Provider.ESEWA
    name = "eSewa"
    SIGNED_FIELDS = "total_amount,transaction_uuid,product_code"
    STATUS_MAP = {
        "COMPLETE": Status.SUCCESSFUL,
        "PENDING": Status.PROCESSING,
        "AMBIGUOUS": Status.PROCESSING,  # "payment is at halt state": keep checking
        "NOT_FOUND": Status.EXPIRED,  # session ended without payment
        "CANCELED": Status.CANCELLED,
        "FULL_REFUND": Status.REFUNDED,
        "PARTIAL_REFUND": Status.PARTIALLY_REFUNDED,
    }

    @staticmethod
    def is_enabled() -> bool:
        return bool(
            settings.ESEWA_ENABLED and settings.ESEWA_PRODUCT_CODE and settings.ESEWA_SECRET_KEY
        )

    @staticmethod
    def sign(message: str) -> str:
        digest = hmac.new(
            settings.ESEWA_SECRET_KEY.encode(), message.encode(), hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode()

    def initiate(self, attempt: PaymentAttempt, *, success_url: str, failure_url: str) -> Redirect:
        total = format_amount(attempt.amount)
        product = settings.ESEWA_PRODUCT_CODE
        message = (
            f"total_amount={total},transaction_uuid={attempt.reference},product_code={product}"
        )
        fields = {
            "amount": total,
            "tax_amount": "0",
            "total_amount": total,
            "transaction_uuid": attempt.reference,
            "product_code": product,
            "product_service_charge": "0",
            "product_delivery_charge": "0",
            "success_url": success_url,
            "failure_url": failure_url,
            "signed_field_names": self.SIGNED_FIELDS,
            "signature": self.sign(message),
        }
        return Redirect(method="POST", url=settings.ESEWA_FORM_URL, fields=fields)

    def read_return(self, encoded: str) -> dict | None:
        """Decode the base64 ``data`` eSewa appends to success_url; None if forged or broken.

        Even a valid one is only used for the audit log: the status API decides.
        """
        try:
            data = json.loads(base64.b64decode(encoded, validate=False))
            names = data["signed_field_names"].split(",")
            message = ",".join(f"{name}={data[name]}" for name in names)
            signature = data["signature"]
        except ValueError, KeyError, TypeError, AttributeError, binascii.Error:
            return None
        return data if hmac.compare_digest(self.sign(message), str(signature)) else None

    def check(self, attempt: PaymentAttempt) -> Result:
        code, data = http_json(
            "GET",
            settings.ESEWA_STATUS_URL,
            params={
                "product_code": settings.ESEWA_PRODUCT_CODE,
                "total_amount": format_amount(attempt.amount),
                "transaction_uuid": attempt.reference,
            },
        )
        gateway_status = str(data.get("status", ""))
        if code != 200 or gateway_status not in self.STATUS_MAP:
            raise GatewayError(data.get("error_message") or f"Unexpected eSewa answer ({code})")
        if data.get("transaction_uuid") not in (None, attempt.reference):
            raise GatewayError("eSewa answered about a different transaction")
        return Result(
            status=self.STATUS_MAP[gateway_status],
            gateway_status=gateway_status,
            amount=_decimal(data.get("total_amount")),
            transaction_id=str(data.get("ref_id") or ""),
            raw=data,
        )


# --- Khalti --------------------------------------------------------------------


class KhaltiGateway:
    code = Provider.KHALTI
    name = "Khalti"
    MIN_AMOUNT = Decimal("10")  # "Amount should be greater than Rs. 10"
    STATUS_MAP = {
        "Completed": Status.SUCCESSFUL,  # the only status to treat as success
        "Pending": Status.PROCESSING,
        "Initiated": Status.INITIATED,
        "Expired": Status.EXPIRED,
        "User canceled": Status.CANCELLED,
        "Refunded": Status.REFUNDED,
        "Partially Refunded": Status.PARTIALLY_REFUNDED,
    }

    @staticmethod
    def is_enabled() -> bool:
        return bool(settings.KHALTI_SECRET_KEY)

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"}

    @staticmethod
    def _url(path: str) -> str:
        return settings.KHALTI_BASE_URL.rstrip("/") + path

    def initiate(self, attempt: PaymentAttempt, *, return_url: str, name: str) -> Redirect:
        paisa = int((attempt.amount * 100).to_integral_value())
        code, data = http_json(
            "POST",
            self._url("/epayment/initiate/"),
            headers=self._headers(),
            body={
                "return_url": return_url,
                "website_url": settings.FRONTEND_URL,
                "amount": paisa,
                "purchase_order_id": attempt.reference,
                "purchase_order_name": name[:100],
            },
        )
        if code != 200 or not data.get("payment_url") or not data.get("pidx"):
            raise GatewayError(f"Khalti refused the payment ({code}): {data}")
        return Redirect(method="GET", url=data["payment_url"], token=data["pidx"], raw=data)

    def check(self, attempt: PaymentAttempt) -> Result:
        if not attempt.gateway_token:
            raise GatewayError("Attempt has no Khalti pidx")
        _, data = http_json(
            "POST",
            self._url("/epayment/lookup/"),
            headers=self._headers(),
            body={"pidx": attempt.gateway_token},
        )
        gateway_status = str(data.get("status", ""))
        if gateway_status not in self.STATUS_MAP:
            raise GatewayError(f"Unexpected Khalti answer: {data}")
        paisa = _decimal(data.get("total_amount"))
        return Result(
            status=self.STATUS_MAP[gateway_status],
            gateway_status=gateway_status,
            amount=paisa / 100 if paisa is not None else None,
            transaction_id=str(data.get("transaction_id") or ""),
            raw=data,
        )


GATEWAYS = {gateway.code: gateway for gateway in (EsewaGateway(), KhaltiGateway())}


def enabled_gateways() -> list:
    return [gateway for gateway in GATEWAYS.values() if gateway.is_enabled()]


def get_gateway(code: str):
    gateway = GATEWAYS.get(code)
    return gateway if gateway and gateway.is_enabled() else None
