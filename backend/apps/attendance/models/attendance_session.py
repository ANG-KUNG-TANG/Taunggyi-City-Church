"""
Attendance session model for Taunggyi City Church.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class AttendanceSession(models.Model):
    """Represents a zone-level or church-wide attendance session."""

    class Scope(models.TextChoices):
        ZONE = "ZONE", "Zone"
        CHURCH_WIDE = "CHURCH_WIDE", "Church-wide"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    activity = models.ForeignKey(
        "tcc.Activity",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="attendance_sessions",
    )

    date = models.DateField()

    start_time = models.TimeField()

    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
    )

    zone = models.ForeignKey(
        "tcc.Zone",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="attendance_sessions",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_attendance_sessions",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_attendance_sessions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "attendance_sessions"
        ordering = ["-date", "-start_time"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(scope="ZONE", zone__isnull=False)
                    | Q(scope="CHURCH_WIDE", zone__isnull=True)
                ),
                name="attendance_session_scope_zone_check",
            ),
        ]

        indexes = [
            models.Index(
                fields=["date", "status"],
                name="attendance_date_status_idx",
            ),
            models.Index(
                fields=["zone", "date"],
                name="attendance_zone_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.date} - {self.get_scope_display()}"
