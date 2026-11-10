"""
Activity model for the Taunggyi City Church system.

Activities are registered under the existing TCC Django app.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Activity(models.Model):
    """
    Represents a church activity.

    Activities support draft editing, publication, and archiving.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    title = models.CharField(
        max_length=200,
    )

    body = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_activities",
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "activities"
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(status="PUBLISHED")
                    | Q(
                        published_by__isnull=False,
                        published_at__isnull=False,
                    )
                ),
                name="activity_published_metadata_required",
            ),
        ]

    def __str__(self):
        return self.title
