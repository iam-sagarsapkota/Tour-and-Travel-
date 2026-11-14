import re

from django.core.exceptions import ValidationError

_SEPARATORS = re.compile(r"[\s\-().]")
_NEPAL_MOBILE = re.compile(r"9[678]\d{8}")
_E164 = re.compile(r"\+[1-9]\d{7,14}")


def normalize_phone(value: str) -> str:
    """Return the number in E.164 form (e.g. +9779812345678) or raise ValidationError.

    A bare 10-digit Nepali mobile number is assumed to be +977; every other
    number must carry its country code (``+`` or ``00`` prefix).
    """
    cleaned = _SEPARATORS.sub("", str(value))
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if _NEPAL_MOBILE.fullmatch(cleaned):
        cleaned = "+977" + cleaned
    if not _E164.fullmatch(cleaned):
        raise ValidationError(
            "Enter a valid phone number including country code, e.g. +9779812345678.",
            code="invalid_phone",
        )
    return cleaned
