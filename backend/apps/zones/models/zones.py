"""
Zone and Zone Leader assignment models.

These models belong to the existing TCC Django app.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Zone(models.Model):
    """
    Represents a church zone.

    A zone may have multiple Zone Leaders.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "zones"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ZoneLeaderAssignment(models.Model):
    """
    Records a Zone Leader's assignment to a zone.

    Assignment history is preserved by setting effective_to
    rather than deleting the assignment.

    A leader may serve multiple zones.
    A zone may have multiple leaders.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="leader_assignments",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="zone_leader_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_zone_leader_assignments",
    )

    effective_from = models.DateTimeField()

    effective_to = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "zone_leader_assignments"
        ordering = ["-effective_from"]

        constraints = [
            models.UniqueConstraint(
                fields=["zone", "user"],
                condition=Q(effective_to__isnull=True),
                name="unique_active_zone_leader_assignment",
            ),
        ]

        indexes = [
            models.Index(
                fields=["zone", "effective_to"],
                name="zone_assignment_active_idx",
            ),
            models.Index(
                fields=["user", "effective_to"],
                name="user_assignment_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.zone}"
