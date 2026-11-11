"""Serializers for aggregate visitor counts."""

from rest_framework import serializers

from apps.attendance.models.visitor_count import VisitorCount


class VisitorCountSerializer(serializers.ModelSerializer):
    """Read representation of a session's visitor count."""

    class Meta:
        model = VisitorCount
        fields = [
            "id",
            "session",
            "count",
            "recorded_by",
            "recorded_at",
            "updated_by",
            "updated_at",
        ]
        read_only_fields = fields


class VisitorCountInputSerializer(serializers.Serializer):
    """Validate a visitor count submission."""

    count = serializers.IntegerField(min_value=0)


class VisitorCountCorrectionSerializer(serializers.Serializer):
    """Validate a Pastor's correction to a visitor count."""

    count = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(
        max_length=500,
        trim_whitespace=True,
        allow_blank=False,
    )
