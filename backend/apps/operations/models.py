from django.conf import settings
from django.db import models

from common.models import BaseModel


class AuditLog(models.Model):
    """Who changed what in the admin area. Append-only."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    action = models.CharField(max_length=40, db_index=True)  # create, update, publish, cancel...
    object_type = models.CharField(max_length=60, db_index=True)  # e.g. "adventures.adventure"
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)  # {"field": [old, new]}
    note = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action} {self.object_type} {self.object_repr}"


class SiteSettings(models.Model):
    """Single row of site-wide settings editable by admins."""

    site_name = models.CharField(max_length=80, default="Himalaya Trails")
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    announcement = models.CharField(
        max_length=240, blank=True, help_text="Short notice shown at the top of the site."
    )
    announcement_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "site settings"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> SiteSettings:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ContactInquiry(BaseModel):
    """A message from the public contact form."""

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=5000)
    handled = models.BooleanField(default=False, db_index=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["handled", "-created_at"]
        verbose_name_plural = "contact inquiries"

    def __str__(self):
        return f"{self.subject} ({self.email})"
