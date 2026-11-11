"""
Attendance session API views.
"""

from uuid import UUID

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.models.activity import Activity
from apps.attendance.models.attendance_session import AttendanceSession
from apps.attendance.permissions.attendance_permissions import IsAttendanceActor
from apps.attendance.selectors.session_selector import AttendanceSessionSelector
from apps.attendance.serializers.session_serializers import (
    AttendanceSessionCreateSerializer,
    AttendanceSessionSerializer,
    AttendanceSessionUpdateSerializer,
)
from apps.attendance.services.attendance_service import AttendanceService
from apps.zones.models.zones import Zone


def _raise_service_error(exc):
    """Translate Django service exceptions into DRF API exceptions."""
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail)

    if isinstance(exc, (DjangoPermissionDenied, PermissionError)):
        raise PermissionDenied(str(exc))

    raise exc


def _correlation_id(request):
    """Read and validate the optional X-Request-ID header."""
    value = request.headers.get("X-Request-ID")

    if not value:
        return None

    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise ValidationError({"X-Request-ID": "A valid UUID is required."})


def _get_accessible_session(user, session_id):
    """Return a session only if it is visible to the requesting user."""
    session = AttendanceSessionSelector.get_session_for_user(
        user=user,
        session_id=session_id,
    )

    if session is None:
        raise NotFound("Attendance session not found.")

    return session


class AttendanceSessionListCreateView(APIView):
    """List accessible sessions or create a new DRAFT session."""

    permission_classes = [IsAttendanceActor]

    def get(self, request):
        sessions = (
            AttendanceSessionSelector.get_sessions_for_user(request.user)
            .select_related(
                "activity",
                "zone",
                "created_by",
                "updated_by",
            )
            .order_by(
                "-date",
                "-start_time",
            )
        )

        zone_id = request.query_params.get("zone_id")
        if zone_id:
            sessions = sessions.filter(zone_id=zone_id)

        session_status = request.query_params.get("status")
        if session_status:
            sessions = sessions.filter(status=session_status)

        serializer = AttendanceSessionSerializer(
            sessions,
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AttendanceSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        zone = None
        zone_id = data.get("zone_id")

        if zone_id is not None:
            zone = Zone.objects.filter(pk=zone_id).first()
            if zone is None:
                raise NotFound("Zone not found.")

        activity = None
        activity_id = data.get("activity_id")

        if activity_id is not None:
            activity = Activity.objects.filter(pk=activity_id).first()
            if activity is None:
                raise NotFound("Activity not found.")

        try:
            session = AttendanceService.create_session(
                actor=request.user,
                date=data["date"],
                start_time=data["start_time"],
                scope=data["scope"],
                zone=zone,
                activity=activity,
                correlation_id=_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AttendanceSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class AttendanceSessionDetailView(APIView):
    """Retrieve or update an accessible session."""

    permission_classes = [IsAttendanceActor]

    def get(self, request, session_id):
        session = _get_accessible_session(
            request.user,
            session_id,
        )

        return Response(
            AttendanceSessionSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, session_id):
        session = _get_accessible_session(
            request.user,
            session_id,
        )

        serializer = AttendanceSessionUpdateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        activity = None
        if "activity_id" in data:
            activity = Activity.objects.filter(pk=data["activity_id"]).first()

            if activity is None:
                raise NotFound("Activity not found.")

        try:
            updated_session = AttendanceService.update_session(
                actor=request.user,
                session_id=session.id,
                date=data.get("date"),
                start_time=data.get("start_time"),
                activity=activity,
                correlation_id=_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AttendanceSessionSerializer(updated_session).data,
            status=status.HTTP_200_OK,
        )


class AttendanceSessionOpenView(APIView):
    """Open an accessible DRAFT session."""

    permission_classes = [IsAttendanceActor]

    def post(self, request, session_id):
        _get_accessible_session(request.user, session_id)

        try:
            session = AttendanceService.open_session(
                actor=request.user,
                session_id=session_id,
                correlation_id=_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AttendanceSessionSerializer(session).data,
            status=status.HTTP_200_OK,
        )


class AttendanceSessionCloseView(APIView):
    """Close an accessible OPEN session."""

    permission_classes = [IsAttendanceActor]

    def post(self, request, session_id):
        _get_accessible_session(request.user, session_id)

        try:
            session = AttendanceService.close_session(
                actor=request.user,
                session_id=session_id,
                correlation_id=_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AttendanceSessionSerializer(session).data,
            status=status.HTTP_200_OK,
        )
