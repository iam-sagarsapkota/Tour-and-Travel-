from django.db import models

from common.models import BaseModel, PublishStatus
from common.uploads import UploadTo, validate_image_upload


class Destination(BaseModel):
    """A trekking region or place (Everest, Annapurna, Langtang, ...).

    Destinations are archived, never deleted: adventures reference them with PROTECT.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    region = models.CharField(
        max_length=80, db_index=True, help_text="Province or broader area, e.g. Gandaki."
    )
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to=UploadTo("destinations"), blank=True, validators=[validate_image_upload]
    )
    best_season = models.CharField(max_length=120, blank=True)
    seasonal_guidance = models.TextField(blank=True)
    attractions = models.TextField(blank=True)
    permit_info = models.TextField(
        blank=True,
        help_text="Informational only. Include the date checked and a link to the official source.",
    )
    status = models.CharField(
        max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT, db_index=True
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name
