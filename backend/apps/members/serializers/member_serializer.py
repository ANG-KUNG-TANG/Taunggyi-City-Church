"""
Serializers for church member listing and creation.
"""

from rest_framework import serializers

from apps.members.models import Member
from apps.zones.models.zones import Zone
from collections.abc import Mapping


class MemberListSerializer(serializers.ModelSerializer):
    """Serialize member information for list responses."""

    zone_name = serializers.CharField(
        source="zone.name",
        read_only=True,
    )

    class Meta:
        model = Member
        fields = [
            "id",
            "zone",
            "zone_name",
            "full_name",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MemberCreateSerializer(serializers.Serializer):
    """Validate member creation requests."""

    zone_id = serializers.PrimaryKeyRelatedField(
        queryset=Zone.objects.filter(is_active=True),
        source="zone",
    )

    full_name = serializers.CharField(
        max_length=200,
        trim_whitespace=True,
    )

    phone = serializers.CharField(
        max_length=40,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )

    address = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )

    def to_internal_value(self, data):
        """Reject fields outside the member creation contract."""

        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        allowed_fields = {
            "zone_id",
            "full_name",
            "phone",
            "address",
            "notes",
        }

        unsupported_fields = set(data.keys()) - allowed_fields

        if unsupported_fields:
            raise serializers.ValidationError(
                {
                    field: "This field is not permitted during member creation."
                    for field in sorted(unsupported_fields)
                }
            )

        return super().to_internal_value(data)

    def validate_full_name(self, value):
        """Reject names containing only whitespace."""

        if not value:
            raise serializers.ValidationError("Full name is required.")

        return value


class MemberUpdateSerializer(serializers.Serializer):
    """Validate ordinary member update requests."""

    expected_version = serializers.IntegerField(
        min_value=1,
        required=True,
    )

    full_name = serializers.CharField(
        max_length=200,
        required=False,
        trim_whitespace=True,
    )

    phone = serializers.CharField(
        max_length=40,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    address = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    is_active = serializers.BooleanField(
        required=False,
    )

    def to_internal_value(self, data):
        """Reject fields outside the ordinary update contract."""

        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        allowed_fields = {
            "expected_version",
            "full_name",
            "phone",
            "address",
            "notes",
            "is_active",
        }

        unsupported_fields = set(data.keys()) - allowed_fields

        if unsupported_fields:
            raise serializers.ValidationError(
                {
                    field: "This field is not permitted in a member update."
                    for field in sorted(unsupported_fields)
                }
            )

        return super().to_internal_value(data)


class MemberTransferSerializer(serializers.Serializer):
    """Validate Pastor-authorised member transfer requests."""

    destination_zone_id = serializers.PrimaryKeyRelatedField(
        queryset=Zone.objects.filter(is_active=True),
        source="destination_zone",
        required=True,
    )

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    expected_version = serializers.IntegerField(
        min_value=1,
        required=True,
    )

    def to_internal_value(self, data):
        """Reject fields outside the transfer contract."""

        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        allowed_fields = {
            "destination_zone_id",
            "reason",
            "expected_version",
        }

        unsupported_fields = set(data.keys()) - allowed_fields

        if unsupported_fields:
            raise serializers.ValidationError(
                {
                    field: "This field is not permitted in a member transfer."
                    for field in sorted(unsupported_fields)
                }
            )

        return super().to_internal_value(data)
