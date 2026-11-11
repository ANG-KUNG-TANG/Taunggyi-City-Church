"""Protected Attendance reporting API."""

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.permissions.attendance_permissions import IsAttendanceActor
from apps.attendance.selectors.attendance_selector import AttendanceSelector


class AttendanceReportQuerySerializer(serializers.Serializer):
    """Validate optional Attendance report date filters."""

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "End date must not precede start date."}
            )

        return attrs


class AttendanceReportItemSerializer(serializers.Serializer):
    """Serialize aggregate data for one accessible session."""

    session_id = serializers.UUIDField(source="id", read_only=True)
    date = serializers.DateField(read_only=True)
    start_time = serializers.TimeField(read_only=True)
    scope = serializers.CharField(read_only=True)
    zone = serializers.CharField(
        source="zone.name",
        allow_null=True,
        read_only=True,
    )
    status = serializers.CharField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    absent_count = serializers.IntegerField(read_only=True)
    visitor_count = serializers.IntegerField(
        source="reported_visitor_count",
        read_only=True,
    )


class AttendanceReportView(APIView):
    """Return aggregate Attendance reports within the user's authorised scope."""

    permission_classes = [IsAttendanceActor]

    def get(self, request):
        query_serializer = AttendanceReportQuerySerializer(
            data=request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        filters = query_serializer.validated_data

        sessions = AttendanceSelector.get_session_report(
            user=request.user,
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
        )

        results = AttendanceReportItemSerializer(
            sessions,
            many=True,
        ).data

        start_date = filters.get("start_date")
        end_date = filters.get("end_date")

        return Response(
            {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "results": results,
            }
        )
