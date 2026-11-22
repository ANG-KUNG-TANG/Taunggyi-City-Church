import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


def content_media_upload_path(instance, filename):
    """Generate a private, unpredictable storage path with a verified extension."""

    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "application/pdf": ".pdf",
    }

    extension = extensions.get(instance.mime_type, ".bin")

    return f"content-media/{instance.id}/{instance.id}{extension}"


class ContentMedia(models.Model):
    class Category(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        DOCUMENT = "DOCUMENT", "Document"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    activity = models.ForeignKey(
        "tcc.Activity",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="media",
    )

    announcement = models.ForeignKey(
        "tcc.Announcement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="media",
    )

    file = models.FileField(
        upload_to=content_media_upload_path,
        max_length=500,
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )

    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField()

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_content_media",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tcc"
        db_table = "content_media"
        ordering = ["created_at"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(activity__isnull=False) & Q(announcement__isnull=True))
                    | (Q(activity__isnull=True) & Q(announcement__isnull=False))
                ),
                name="content_media_exactly_one_parent",
            ),
            models.CheckConstraint(
                condition=Q(file_size__gt=0),
                name="content_media_positive_file_size",
            ),
        ]

        indexes = [
            models.Index(
                fields=["activity", "created_at"],
                name="idx_media_activity",
            ),
            models.Index(
                fields=["announcement", "created_at"],
                name="idx_media_announcement",
            ),
        ]

    def __str__(self):
        return f"{self.category}:{self.id}"
