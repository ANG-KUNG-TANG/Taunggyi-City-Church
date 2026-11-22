"""
Serializers for the Taunggyi City Church announcement module.
"""

from rest_framework import serializers

from apps.announcements.models.announcement import Announcement
from apps.announcements.validators import validate_announcement_content
from apps.content_media.serializers.media_serializer import (
    ContentMediaPublicSerializer,
)


class AnnouncementSerializer(serializers.ModelSerializer):
    """Serialize announcement data and validate editable content."""

    media = ContentMediaPublicSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "body",
            "status",
            "published_by",
            "published_at",
            "media",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "published_by",
            "published_at",
            "media",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        """Validate the complete content, including partial updates."""

        title = attrs.get("title")
        body = attrs.get("body")

        if self.instance is not None:
            title = title if title is not None else self.instance.title
            body = body if body is not None else self.instance.body

        if title is not None and body is not None:
            normalized = validate_announcement_content(
                title=title,
                body=body,
            )
            attrs.update(normalized)

        return attrs
