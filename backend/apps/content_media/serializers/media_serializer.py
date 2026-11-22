"""
Serializers for shared Activity and Announcement media.
"""

from django.urls import reverse
from rest_framework import serializers

from apps.content_media.models.content_media import ContentMedia


class ContentMediaPublicSerializer(serializers.ModelSerializer):
    """Expose safe media metadata and its protected download endpoint."""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ContentMedia
        fields = [
            "id",
            "category",
            "original_filename",
            "mime_type",
            "file_size",
            "file_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        """Return the application-controlled media download endpoint."""

        return reverse(
            "content-media-file",
            kwargs={"media_id": obj.id},
        )


class ContentMediaSerializer(serializers.ModelSerializer):
    """Expose safe media metadata without revealing storage details."""

    class Meta:
        model = ContentMedia
        fields = [
            "id",
            "category",
            "original_filename",
            "mime_type",
            "file_size",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ContentMediaUploadSerializer(serializers.Serializer):
    """Accept a file for server-side validation and processing."""

    file = serializers.FileField(
        write_only=True,
        allow_empty_file=False,
    )
