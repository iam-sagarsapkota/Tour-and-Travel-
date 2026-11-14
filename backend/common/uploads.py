import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@deconstructible
class UploadTo:
    """Store uploads under ``prefix`` with a random name; the client's filename is discarded."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(self, instance, filename: str) -> str:
        return f"{self.prefix}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def validate_image_upload(file) -> None:
    """Extension and size checks. ImageField separately verifies the bytes are a real image."""
    if Path(file.name).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Upload a JPG, PNG or WebP image.", code="invalid_extension")
    if file.size > settings.MAX_IMAGE_UPLOAD_BYTES:
        limit_mb = settings.MAX_IMAGE_UPLOAD_BYTES / (1024 * 1024)
        raise ValidationError(f"Image must be {limit_mb:g} MB or smaller.", code="file_too_large")
