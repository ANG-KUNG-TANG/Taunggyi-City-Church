"""
Activity serializers for the Taunggyi City Church system.
"""

from rest_framework import serializers

from apps.activities.models.activity import Activity


class ActivitySerializer(serializers.ModelSerializer):
    """Serialize activity data while protecting publication metadata."""

    published_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    published_at = serializers.DateTimeField(
        read_only=True,
    )

    status = serializers.CharField(
        read_only=True,
    )

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "body",
            "status",
            "published_by",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "published_by",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        """Require a non-empty title within the model's limit."""

        if not value or not value.strip():
            raise serializers.ValidationError("Title is required.")

        if len(value.strip()) > 200:
            raise serializers.ValidationError("Title must not exceed 200 characters.")

        return value.strip()

    def validate_body(self, value):
        """Require non-empty activity content."""

        if not value or not value.strip():
            raise serializers.ValidationError("Activity body is required.")

        return value.strip()
