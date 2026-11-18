"""
Serializer for detailed church member information.
"""

from rest_framework import serializers

from apps.members.models import Member


class MemberDetailSerializer(serializers.ModelSerializer):
    """Serialize complete member details with protected metadata."""

    zone_name = serializers.CharField(
        source="zone.name",
        read_only=True,
    )

    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
    )

    updated_by_email = serializers.EmailField(
        source="updated_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Member
        fields = [
            "id",
            "zone",
            "zone_name",
            "full_name",
            "phone",
            "address",
            "notes",
            "is_active",
            "version",
            "created_by",
            "created_by_email",
            "updated_by",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "zone",
            "zone_name",
            "version",
            "created_by",
            "created_by_email",
            "updated_by",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]

    def validate_full_name(self, value):
        """Require a non-empty member name."""

        value = value.strip()

        if not value:
            raise serializers.ValidationError("Full name is required.")

        if len(value) > 200:
            raise serializers.ValidationError("Full name cannot exceed 200 characters.")

        return value

    def validate_phone(self, value):
        """Normalize and validate the phone number."""

        value = value.strip()

        if len(value) > 40:
            raise serializers.ValidationError("Phone cannot exceed 40 characters.")

        return value

    def validate_address(self, value):
        return value.strip()

    def validate_notes(self, value):
        return value.strip()
