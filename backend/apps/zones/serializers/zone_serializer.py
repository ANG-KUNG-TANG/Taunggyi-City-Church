from rest_framework import serializers

from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ZoneLeaderAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )
    assigned_by_email = serializers.EmailField(
        source="assigned_by.email",
        read_only=True,
    )

    class Meta:
        model = ZoneLeaderAssignment
        fields = [
            "id",
            "zone",
            "user",
            "user_email",
            "assigned_by",
            "assigned_by_email",
            "effective_from",
            "effective_to",
            "created_at",
        ]
        read_only_fields = fields


class ZoneLeaderAssignmentCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    effective_from = serializers.DateTimeField(required=False)
