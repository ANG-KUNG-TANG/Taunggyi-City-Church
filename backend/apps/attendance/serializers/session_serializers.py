"""Serializers for Attendance session requests and responses."""

from rest_framework import serializers

from apps.attendance.models.attendance_session import AttendanceSession


class AttendanceSessionSerializer(serializers.ModelSerializer):
    """Read representation of an Attendance session."""

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "activity",
            "date",
            "start_time",
            "scope",
            "zone",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AttendanceSessionCreateSerializer(serializers.Serializer):
    """Validate data required to create an Attendance session."""

    activity_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    date = serializers.DateField()
    start_time = serializers.TimeField()
    scope = serializers.ChoiceField(
        choices=AttendanceSession.Scope.choices,
    )
    zone_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        scope = attrs["scope"]
        zone_id = attrs.get("zone_id")

        if scope == AttendanceSession.Scope.ZONE and zone_id is None:
            raise serializers.ValidationError(
                {"zone_id": "A zone is required for a zone-specific session."}
            )

        if scope == AttendanceSession.Scope.CHURCH_WIDE and zone_id is not None:
            raise serializers.ValidationError(
                {"zone_id": "A church-wide session cannot have a zone."}
            )

        return attrs


class AttendanceSessionUpdateSerializer(serializers.Serializer):
    """Validate fields that may be changed on a DRAFT session."""

    activity_id = serializers.UUIDField(required=False)
    date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided.")
        return attrs
