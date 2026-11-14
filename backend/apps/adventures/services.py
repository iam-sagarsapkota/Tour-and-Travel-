"""Publication workflow for adventures: draft -> published -> archived."""

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.models import PublishStatus

from .models import Adventure


def publish(adventure: Adventure) -> Adventure:
    if adventure.destination.status != PublishStatus.PUBLISHED:
        raise ValidationError(
            {"destination": ["Publish the destination before publishing this adventure."]}
        )
    adventure.status = PublishStatus.PUBLISHED
    adventure.published_at = adventure.published_at or timezone.now()
    adventure.save(update_fields=["status", "published_at", "updated_at"])
    return adventure


def set_status(adventure: Adventure, status: str) -> Adventure:
    """Move to draft or archived. Hidden from the public catalog either way."""
    adventure.status = status
    adventure.save(update_fields=["status", "updated_at"])
    return adventure
