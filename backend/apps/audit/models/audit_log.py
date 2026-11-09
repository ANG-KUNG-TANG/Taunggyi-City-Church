"""
Append-only audit log model.

The model belongs to the existing TCC Django app so that
its database table is managed by the tcc migrations.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLogQuerySet(models.QuerySet):
    """
    Prevent ordinary queryset updates and deletions.
    """

    def update(self, **kwargs):
        raise ValidationError("Audit records cannot be updated.")

    def delete(self):
        raise ValidationError("Audit records cannot be deleted.")


class AuditLog(models.Model):
    """
    Immutable record of a sensitive system action.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        AUTHORISE = "AUTHORISE", "Authorise"
        REJECT = "REJECT", "Reject"
        CORRECT = "CORRECT", "Correct"
        REVERSE = "REVERSE", "Reverse"
        PUBLISH = "PUBLISH", "Publish"
        ROLE_CHANGE = "ROLE_CHANGE", "Role change"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    entity_type = models.CharField(
        max_length=80,
    )

    entity_id = models.UUIDField()

    action = models.CharField(
        max_length=40,
        choices=Action.choices,
    )

    before_data = models.JSONField(
        null=True,
        blank=True,
    )

    after_data = models.JSONField(
        null=True,
        blank=True,
    )

    occurred_at = models.DateTimeField(
        auto_now_add=True,
    )

    correlation_id = models.UUIDField(
        null=True,
        blank=True,
    )

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        app_label = "tcc"
        db_table = "audit_logs"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=[
                    "entity_type",
                    "entity_id",
                    "occurred_at",
                ],
                name="idx_audit_entity",
            ),
            models.Index(
                fields=[
                    "actor",
                    "occurred_at",
                ],
                name="idx_audit_actor",
            ),
        ]

    def save(self, *args, **kwargs):
        """
        Permit creation but reject ordinary updates.
        """
        if not self._state.adding:
            raise ValidationError("Audit records cannot be updated.")

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Reject ordinary instance deletion.
        """
        raise ValidationError("Audit records cannot be deleted.")

    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} " f"{self.action}"
