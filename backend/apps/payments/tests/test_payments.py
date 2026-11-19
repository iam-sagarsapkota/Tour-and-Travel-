import base64
import datetime as dt
import json
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings import services as booking_services
from apps.bookings.models import Booking
from apps.payments import gateways, services
from apps.payments.models import Payment, PaymentAttempt, PaymentLog

pytestmark = pytest.mark.django_db

INITIATE = reverse("payments:initiate")
VERIFY = reverse("payments:verify")


class FakeHTTP:
    """Replaces gateways.http_json; records calls and replays scripted answers."""

    def __init__(self):
        self.calls = []
        self.answers = []  # list of (status, body) or Exception

    def answer(self, status, body):
        self.answers.append((status, body))

    def fail(self, message="connection refused"):
        self.answers.append(gateways.GatewayError(message))

    def __call__(self, method, url, *, params=None, body=None, headers=None):
        self.calls.append(
            {"method": method, "url": url, "params": params, "body": body, "headers": headers}
        )
        if not self.answers:
            raise AssertionError(f"Unexpected provider call: {method} {url}")
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def http(monkeypatch):
    fake = FakeHTTP()
    monkeypatch.setattr(gateways, "http_json", fake)
    return fake


@pytest.fixture
def booking(user, make_departure):
    departure = make_departure(price_override="38000.00", capacity=4)
    return booking_services.create_booking(
        user=user,
        departure_id=departure.pk,
        participants=[{"full_name": "Pasang Sherpa"}, {"full_name": "Dawa Lama"}],
        policy_accepted=True,
    )


def esewa_status(attempt, status="COMPLETE", amount=None, ref_id="0007G36"):
    return {
        "product_code": "EPAYTEST",
        "transaction_uuid": attempt.reference,
        "total_amount": float(amount if amount is not None else attempt.amount),
        "status": status,
        "ref_id": ref_id,
    }


def start(booking, provider="esewa"):
    attempt, redirect = services.initiate_payment(booking=booking, provider=provider)
    return attempt, redirect


class TestEsewaSigning:
    def test_signature_matches_esewa_sandbox_rule(self, settings):
        # Verified against the live sandbox: this rule is accepted, others get ES104.
        settings.ESEWA_SECRET_KEY = "8gBm/:&EnhH.1/q"
        assert (
            gateways.EsewaGateway.sign(
                "total_amount=100,transaction_uuid=HT-TEST-1,product_code=EPAYTEST"
            )
            == "QpxlRcSJlAkMnrd5b9PSVas1rgWRQgQTPzZmB0Yay7M="
        )

    @pytest.mark.parametrize(
        ("amount", "text"),
        [("38000.00", "38000"), ("19999.50", "19999.5"), ("100.05", "100.05")],
    )
    def test_amount_format(self, amount, text):
        assert gateways.format_amount(Decimal(amount)) == text

    def test_initiate_builds_signed_form_and_extends_hold(self, booking, settings):
        settings.PAYMENT_HOLD_MINUTES = 20
        before = booking.expires_at

        attempt, redirect = start(booking)

        assert redirect["method"] == "POST"
        assert redirect["url"] == settings.ESEWA_FORM_URL
        fields = redirect["fields"]
        assert fields["total_amount"] == fields["amount"] == "76000"
        assert fields["transaction_uuid"] == attempt.reference
        assert attempt.reference.startswith(booking.reference + "-")
        assert set(attempt.reference) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
        assert fields["success_url"] == f"https://trails.test/payments/esewa/{attempt.pk}/success"
        message = f"total_amount=76000,transaction_uuid={attempt.reference},product_code=EPAYTEST"
        assert fields["signature"] == gateways.EsewaGateway.sign(message)
        booking.refresh_from_db()
        assert booking.expires_at > before
        assert Payment.objects.get(booking=booking).amount == Decimal("76000.00")

    def test_return_data_signature_is_checked(self):
        gateway = gateways.EsewaGateway()
        data = {
            "transaction_code": "0LD5CEH",
            "status": "COMPLETE",
            "total_amount": "76,000.0",
            "transaction_uuid": "HT-X-1",
            "product_code": "EPAYTEST",
            "signed_field_names": (
                "transaction_code,status,total_amount,transaction_uuid,product_code,"
                "signed_field_names"
            ),
        }
        message = ",".join(f"{k}={data[k]}" for k in data["signed_field_names"].split(","))
        data["signature"] = gateway.sign(message)
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        assert gateway.read_return(encoded)["transaction_code"] == "0LD5CEH"

        data["total_amount"] = "1.0"  # tampered after signing
        forged = base64.b64encode(json.dumps(data).encode()).decode()
        assert gateway.read_return(forged) is None
        assert gateway.read_return("not base64 at all!!") is None


class TestVerification:
    def test_complete_confirms_booking(self, booking, http):
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt))

        result = services.verify_attempt(attempt)

        assert result.status == PaymentAttempt.Status.SUCCESSFUL
        assert result.gateway_transaction_id == "0007G36"
        payment = Payment.objects.get(booking=booking)
        assert payment.status == Payment.Status.SUCCESSFUL
        assert payment.provider == "esewa"
        assert payment.gateway_reference == "0007G36"
        assert not payment.needs_attention
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED
        # The status check used our record, not anything from the browser.
        assert http.calls[0]["params"] == {
            "product_code": "EPAYTEST",
            "total_amount": "76000",
            "transaction_uuid": attempt.reference,
        }

    def test_duplicate_verification_is_idempotent(self, booking, http):
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt))
        services.verify_attempt(attempt)

        attempt.refresh_from_db()
        services.verify_attempt(attempt)  # e.g. browser refresh on the return page

        assert len(http.calls) == 1
        assert booking.events.filter(to_status="confirmed").count() == 1

    def test_concurrent_results_apply_once(self, booking, http):
        attempt, _ = start(booking)
        result = gateways.Result(
            status=PaymentAttempt.Status.SUCCESSFUL,
            gateway_status="COMPLETE",
            amount=attempt.amount,
            transaction_id="T1",
        )
        now = timezone.now()
        services._apply(attempt.pk, result, now)
        services._apply(attempt.pk, result, now)  # second callback racing the first

        assert booking.events.filter(to_status="confirmed").count() == 1
        assert not Payment.objects.get(booking=booking).needs_attention

    def test_amount_mismatch_is_not_success(self, booking, http):
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt, amount="100"))

        result = services.verify_attempt(attempt)

        assert result.status == PaymentAttempt.Status.FAILED
        payment = Payment.objects.get(booking=booking)
        assert payment.status != Payment.Status.SUCCESSFUL
        assert payment.needs_attention
        assert "100" in payment.attention_reason
        booking.refresh_from_db()
        assert booking.status == Booking.Status.PENDING

    @pytest.mark.parametrize(
        ("gateway_status", "attempt_status", "payment_status"),
        [
            ("PENDING", "processing", "processing"),
            ("AMBIGUOUS", "processing", "processing"),
            ("CANCELED", "cancelled", "cancelled"),
        ],
    )
    def test_non_success_statuses(
        self, booking, http, gateway_status, attempt_status, payment_status
    ):
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt, status=gateway_status, ref_id=None))

        result = services.verify_attempt(attempt)

        assert result.status == attempt_status
        assert Payment.objects.get(booking=booking).status == payment_status
        booking.refresh_from_db()
        assert booking.status == Booking.Status.PENDING

    def test_not_found_is_only_final_after_grace_period(self, booking, http, settings):
        settings.PAYMENT_ATTEMPT_GRACE_MINUTES = 30
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt, status="NOT_FOUND", ref_id=None))
        assert services.verify_attempt(attempt).status == PaymentAttempt.Status.PROCESSING

        later = timezone.now() + dt.timedelta(minutes=31)
        http.answer(200, esewa_status(attempt, status="NOT_FOUND", ref_id=None))
        assert services.verify_attempt(attempt, now=later).status == PaymentAttempt.Status.EXPIRED

    def test_provider_outage_leaves_attempt_open(self, booking, http):
        attempt, _ = start(booking)
        http.fail()

        result = services.verify_attempt(attempt)

        assert result.status == PaymentAttempt.Status.INITIATED
        assert PaymentLog.objects.filter(attempt=attempt, kind="error").exists()

    def test_initiation_failure_is_reported(self, booking, http):
        http.fail()
        with pytest.raises(services.PaymentProviderUnavailable):
            start(booking, "khalti")
        assert PaymentAttempt.objects.get().status == PaymentAttempt.Status.FAILED


class TestRecovery:
    def test_paid_after_hold_lapsed_reserves_seats_again(self, booking, http):
        attempt, _ = start(booking)
        Booking.objects.filter(pk=booking.pk).update(
            expires_at=timezone.now() - dt.timedelta(minutes=1)
        )
        booking_services.expire_pending_bookings()
        booking.refresh_from_db()
        assert booking.status == Booking.Status.EXPIRED
        http.answer(200, esewa_status(attempt))

        services.verify_attempt(attempt)

        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED
        booking.departure.refresh_from_db()
        assert booking.departure.seats_reserved == 2
        assert not Payment.objects.get(booking=booking).needs_attention

    def test_paid_after_seats_sold_is_flagged_for_refund(self, booking, http, make_user):
        attempt, _ = start(booking)
        Booking.objects.filter(pk=booking.pk).update(
            expires_at=timezone.now() - dt.timedelta(minutes=1)
        )
        booking_services.expire_pending_bookings()
        booking_services.create_booking(
            user=make_user(),
            departure_id=booking.departure_id,
            participants=[{"full_name": f"P{n}"} for n in range(4)],
            policy_accepted=True,
        )
        http.answer(200, esewa_status(attempt))

        services.verify_attempt(attempt)

        payment = Payment.objects.get(booking=booking)
        assert payment.status == Payment.Status.SUCCESSFUL
        assert payment.needs_attention
        assert "Refund" in payment.attention_reason
        booking.refresh_from_db()
        assert booking.status == Booking.Status.EXPIRED

    def test_second_successful_attempt_is_flagged_as_duplicate(self, booking, http):
        first, _ = start(booking)
        second, _ = start(booking)
        http.answer(200, esewa_status(first, ref_id="A"))
        services.verify_attempt(first)

        http.answer(200, esewa_status(second, ref_id="B"))
        services.verify_attempt(second)

        payment = Payment.objects.get(booking=booking)
        assert payment.gateway_reference == "A"
        assert payment.needs_attention
        assert "Duplicate" in payment.attention_reason

    def test_cannot_start_payment_for_paid_or_expired_booking(
        self, booking, http, user, make_departure
    ):
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt))
        services.verify_attempt(attempt)
        with pytest.raises(Exception) as paid:
            start(booking)
        assert getattr(paid.value.detail, "code", "") == "already_paid"

        stale = booking_services.create_booking(
            user=user,
            departure_id=make_departure().pk,
            participants=[{"full_name": "A"}],
            policy_accepted=True,
            now=timezone.now() - dt.timedelta(hours=1),
        )
        with pytest.raises(Exception) as expired:
            start(stale)
        assert getattr(expired.value.detail, "code", "") == "booking_expired"


class TestKhalti:
    def test_initiate_sends_paisa_and_key(self, booking, http):
        http.answer(
            200,
            {
                "pidx": "bZQLD9wRVWo4CdESSfuSsB",
                "payment_url": "https://test-pay.khalti.com/?pidx=bZQLD9wRVWo4CdESSfuSsB",
                "expires_at": "2026-12-01T10:00:00+05:45",
                "expires_in": 1800,
            },
        )

        attempt, redirect = start(booking, "khalti")

        call = http.calls[0]
        assert call["url"] == "https://dev.khalti.com/api/v2/epayment/initiate/"
        assert call["headers"] == {"Authorization": "Key test-khalti-secret"}
        assert call["body"]["amount"] == 7_600_000
        assert call["body"]["purchase_order_id"] == attempt.reference
        assert (
            call["body"]["return_url"] == f"https://trails.test/payments/khalti/{attempt.pk}/return"
        )
        assert redirect == {
            "method": "GET",
            "url": "https://test-pay.khalti.com/?pidx=bZQLD9wRVWo4CdESSfuSsB",
            "fields": {},
        }
        attempt.refresh_from_db()
        assert attempt.gateway_token == "bZQLD9wRVWo4CdESSfuSsB"

    def _started(self, booking, http):
        http.answer(
            200, {"pidx": "PIDX1", "payment_url": "https://test-pay.khalti.com/?pidx=PIDX1"}
        )
        attempt, _ = start(booking, "khalti")
        return attempt

    def test_completed_lookup_confirms(self, booking, http):
        attempt = self._started(booking, http)
        http.answer(
            200,
            {
                "pidx": "PIDX1",
                "total_amount": 7_600_000,
                "status": "Completed",
                "transaction_id": "GFq9PFS7b2iYvL8Lir9oXe",
                "fee": 0,
                "refunded": False,
            },
        )

        assert services.verify_attempt(attempt).status == PaymentAttempt.Status.SUCCESSFUL
        assert http.calls[1]["body"] == {"pidx": "PIDX1"}
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED

    def test_user_canceled_comes_back_as_http_400(self, booking, http):
        attempt = self._started(booking, http)
        http.answer(
            400,
            {
                "pidx": "PIDX1",
                "total_amount": 7_600_000,
                "status": "User canceled",
                "transaction_id": None,
                "fee": 0,
                "refunded": False,
            },
        )

        assert services.verify_attempt(attempt).status == PaymentAttempt.Status.CANCELLED

    def test_minimum_amount(self, user, make_departure, http):
        cheap = booking_services.create_booking(
            user=user,
            departure_id=make_departure(price_override="5.00").pk,
            participants=[{"full_name": "A"}],
            policy_accepted=True,
        )
        with pytest.raises(Exception) as exc:
            start(cheap, "khalti")
        assert "provider" in exc.value.detail

    def test_disabled_without_key(self, booking, settings):
        settings.KHALTI_SECRET_KEY = ""
        with pytest.raises(Exception) as exc:
            start(booking, "khalti")
        assert "provider" in exc.value.detail


class TestReconciliation:
    def test_settles_abandoned_attempts_only_when_old_enough(self, booking, http):
        attempt, _ = start(booking)
        assert services.reconcile_open_attempts() == 0  # too new: nobody asked
        assert http.calls == []

        later = timezone.now() + dt.timedelta(minutes=6)
        http.answer(200, esewa_status(attempt))
        assert services.reconcile_open_attempts(now=later) == 1
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED

    def test_celery_task(self, booking, http):
        from apps.payments.tasks import reconcile_open_attempts_task

        assert reconcile_open_attempts_task.delay().get() == 0


class TestApi:
    def test_providers_lists_enabled_methods(self, auth_client, user, settings):
        settings.KHALTI_SECRET_KEY = ""
        response = auth_client(user).get(reverse("payments:providers"))
        assert response.data == [{"code": "esewa", "name": "eSewa"}]

    def test_initiate_requires_owner(self, auth_client, make_user, booking):
        other = auth_client(make_user())
        response = other.post(INITIATE, {"booking": str(booking.pk), "provider": "esewa"})
        assert response.status_code == 404

    def test_initiate_and_verify_flow(self, auth_client, user, booking, http):
        client = auth_client(user)
        started = client.post(INITIATE, {"booking": str(booking.pk), "provider": "esewa"})
        assert started.status_code == 200
        assert started.data["method"] == "POST"
        attempt = PaymentAttempt.objects.get(pk=started.data["attempt"])
        http.answer(200, esewa_status(attempt))

        verified = client.post(
            VERIFY,
            {"attempt": str(attempt.pk), "params": {"data": "forged-or-not, it is only logged"}},
            format="json",
        )

        assert verified.status_code == 200
        assert verified.data["attempt"]["status"] == "successful"
        assert verified.data["payment"]["booking_status"] == "confirmed"
        assert PaymentLog.objects.filter(attempt=attempt, kind="return").exists()
        booking_view = client.get(reverse("bookings:booking-detail", args=[booking.pk]))
        assert booking_view.data["payment"]["status"] == "successful"

    def test_verify_requires_owner(self, auth_client, make_user, booking):
        attempt, _ = start(booking)
        response = auth_client(make_user()).post(
            VERIFY, {"attempt": str(attempt.pk)}, format="json"
        )
        assert response.status_code == 404

    def test_history_lists_own_payments(self, auth_client, user, make_user, booking):
        start(booking)
        client = auth_client(user)
        rows = client.get(reverse("payments:history")).data["results"]
        assert [row["booking_reference"] for row in rows] == [booking.reference]
        assert auth_client(make_user()).get(reverse("payments:history")).data["count"] == 0

    def test_admin_lists_flags_and_resolves(self, auth_client, admin_user, user, booking, http):
        attempt, _ = start(booking)
        http.answer(200, esewa_status(attempt, amount="1"))
        services.verify_attempt(attempt)
        client = auth_client(admin_user)
        url = reverse("admin_payments:payment-list")

        assert auth_client(user).get(url).status_code == 403
        flagged = client.get(url, {"needs_attention": "true"}).data["results"]
        assert len(flagged) == 1
        assert flagged[0]["logs"]

        resolve = reverse("admin_payments:payment-resolve", args=[flagged[0]["id"]])
        assert client.post(resolve, {}).status_code == 400
        done = client.post(resolve, {"note": "Contacted eSewa; no money captured."})
        assert done.status_code == 200
        assert done.data["needs_attention"] is False

    def test_admin_cannot_edit_payments(self, auth_client, admin_user, booking):
        start(booking)
        payment = Payment.objects.get()
        url = reverse("admin_payments:payment-detail", args=[payment.pk])
        assert auth_client(admin_user).patch(url, {"amount": "1"}).status_code == 405
