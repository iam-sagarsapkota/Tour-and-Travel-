"""Audit trail for admin changes (PRD §9.2: changes affecting bookings/payments must be audited)."""

import datetime as dt
import decimal
import uuid

from django.db import models

from .models import AuditLog

# Never written to the audit trail, even as "changed".
SECRET_FIELDS = {"password"}


def _plain(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (decimal.Decimal, uuid.UUID, dt.date, dt.datetime)):
        return str(value)
    if isinstance(value, models.Model):
        return str(value.pk)
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if hasattr(value, "name"):  # uploaded files
        return value.name
    return str(value)


def snapshot(instance, fields) -> dict:
    return {name: _plain(getattr(instance, name, None)) for name in fields}


def diff(before: dict, after: dict) -> dict:
    changes = {}
    for name in after:
        if name in SECRET_FIELDS:
            continue
        if before.get(name) != after[name]:
            changes[name] = [before.get(name), after[name]]
    return changes


def client_ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR") if request else None


def record(*, actor, action: str, obj, changes: dict | None = None, note: str = "", request=None):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj._meta.label_lower,
        object_id=str(obj.pk),
        object_repr=str(obj)[:200],
        changes=changes or {},
        note=note,
        ip_address=client_ip(request),
    )


class AuditedViewSetMixin:
    """Log create/update/delete done through an admin ModelViewSet."""

    def _fields(self, serializer):
        return [name for name in serializer.validated_data if name not in SECRET_FIELDS]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record(
            actor=self.request.user,
            action="create",
            obj=serializer.instance,
            changes={
                k: [None, v]
                for k, v in snapshot(serializer.instance, self._fields(serializer)).items()
            },
            request=self.request,
        )

    def perform_update(self, serializer):
        fields = self._fields(serializer)
        before = snapshot(serializer.instance, fields)
        super().perform_update(serializer)
        changes = diff(before, snapshot(serializer.instance, fields))
        if "password" in serializer.validated_data:
            changes["password"] = ["(hidden)", "(changed)"]
        if changes:
            record(
                actor=self.request.user,
                action="update",
                obj=serializer.instance,
                changes=changes,
                request=self.request,
            )
        self.after_update(serializer.instance, changes)

    def after_update(self, instance, changes):
        """Hook for side effects of an audited change (e.g. notifying travellers)."""

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        record(actor=self.request.user, action="delete", obj=instance, request=self.request)
