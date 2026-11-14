import uuid

from django.db import models
from django.utils.text import slugify


class PublishStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class BaseModel(models.Model):
    """UUID primary key (safe to expose) plus UTC audit timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def generate_unique_slug(model, source: str, max_length: int = 120) -> str:
    """Slugify ``source`` and append -2, -3, ... until it is unused on ``model``."""
    base = slugify(source)[: max_length - 6] or "item"
    slug, suffix = base, 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug
