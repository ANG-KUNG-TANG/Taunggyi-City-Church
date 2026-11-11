"""
Aggregate visitor count for attendance sessions.
"""

import uuid

from django.conf import settings
from django.db import models


class VisitorCount(models.Model):
    """Stores the aggregate visitor count for one attendance session."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.OneToOneField(
        "tcc.AttendanceSession",
        on_delete=models.PROTECT,
        related_name="visitor_count",
    )

    count = models.PositiveIntegerField(
        default=0,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_visitor_counts",
    )

    recorded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_visitor_counts",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "visitor_counts"

    def __str__(self):
        return f"{self.session} - {self.count} visitors"
