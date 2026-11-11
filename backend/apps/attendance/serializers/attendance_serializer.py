"""Serializers for member attendance recording and correction."""

from rest_framework import serializers

from apps.attendance.models.member_attendance import MemberAttendance


class MemberAttendanceSerializer(serializers.ModelSerializer):
    """Read representation of a member attendance record."""

    class Meta:
        model = MemberAttendance
        fields = [
            "id",
            "session",
            "member",
            "status",
            "recorded_by",
            "recorded_at",
            "updated_by",
            "updated_at",
        ]
        read_only_fields = fields


class MemberAttendanceInputSerializer(serializers.Serializer):
    """Validate one member attendance entry."""

    member_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=MemberAttendance.Status.choices,
    )


class MemberAttendanceBulkSerializer(serializers.Serializer):
    """Validate a batch of member attendance entries."""

    records = MemberAttendanceInputSerializer(
        many=True,
        allow_empty=False,
    )

    def validate_records(self, records):
        member_ids = [record["member_id"] for record in records]

        if len(member_ids) != len(set(member_ids)):
            raise serializers.ValidationError(
                "A member may appear only once in an attendance batch."
            )

        return records


class AttendanceCorrectionSerializer(serializers.Serializer):
    """Validate a Pastor's correction to a closed-session record."""

    status = serializers.ChoiceField(
        choices=MemberAttendance.Status.choices,
    )
    reason = serializers.CharField(
        max_length=500,
        trim_whitespace=True,
        allow_blank=False,
    )
