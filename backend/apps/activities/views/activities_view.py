"""
Activity API views for public access and authorised management.
"""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.permissions.activities_permissions import (
    IsActivityManager,
)
from apps.activities.selectors.activities_selectors import ActivitySelector
from apps.activities.serializers.activities_serializers import ActivitySerializer
from apps.activities.services.activities_services import ActivityService


def _raise_service_error(exc):
    """Translate service-layer exceptions into appropriate API errors."""
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail)
    if isinstance(exc, (DjangoPermissionDenied, PermissionError)):
        raise PermissionDenied(str(exc))
    raise exc


class PublicActivityListView(APIView):
    """Return published activities only."""

    permission_classes = [AllowAny]

    def get(self, request):
        activities = ActivitySelector.get_published_activities()
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicActivityDetailView(APIView):
    """Return one published activity."""

    permission_classes = [AllowAny]

    def get(self, request, activity_id):
        activity = ActivitySelector.get_published_activity_by_id(activity_id)
        if activity is None:
            raise NotFound("Published activity not found.")

        serializer = ActivitySerializer(activity)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActivityManagementListView(APIView):
    """List all activities for authorised managers."""

    permission_classes = [IsActivityManager]

    def get(self, request):
        activities = ActivitySelector.get_all_activities()
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActivityCreateView(APIView):
    """Create a draft activity."""

    permission_classes = [IsActivityManager]

    def post(self, request):
        serializer = ActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            activity = ActivityService.create_activity(
                actor=request.user,
                title=serializer.validated_data["title"],
                body=serializer.validated_data["body"],
            )
        except (DjangoValidationError, DjangoPermissionDenied, PermissionError) as exc:
            _raise_service_error(exc)

        return Response(
            ActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED,
        )


class ActivityManagementDetailView(APIView):
    """Retrieve or update an activity for authorised managers."""

    permission_classes = [IsActivityManager]

    def get(self, request, activity_id):
        activity = ActivitySelector.get_activity_by_id(activity_id)
        if activity is None:
            raise NotFound("Activity not found.")

        return Response(
            ActivitySerializer(activity).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, activity_id):
        return self._update(request, activity_id, partial=False)

    def patch(self, request, activity_id):
        return self._update(request, activity_id, partial=True)

    def _update(self, request, activity_id, *, partial):
        activity = ActivitySelector.get_activity_by_id(activity_id)
        if activity is None:
            raise NotFound("Activity not found.")

        serializer = ActivitySerializer(
            activity,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated_activity = ActivityService.update_activity(
                actor=request.user,
                activity_id=activity_id,
                title=serializer.validated_data.get("title", activity.title),
                body=serializer.validated_data.get("body", activity.body),
            )
        except (DjangoValidationError, DjangoPermissionDenied, PermissionError) as exc:
            _raise_service_error(exc)

        return Response(
            ActivitySerializer(updated_activity).data,
            status=status.HTTP_200_OK,
        )


class ActivityPublishView(APIView):
    """Publish an activity; permission is enforced server-side."""

    permission_classes = [IsActivityManager]

    def post(self, request, activity_id):
        try:
            activity = ActivityService.publish_activity(
                actor=request.user,
                activity_id=activity_id,
            )
        except (DjangoValidationError, DjangoPermissionDenied, PermissionError) as exc:
            _raise_service_error(exc)

        return Response(
            ActivitySerializer(activity).data,
            status=status.HTTP_200_OK,
        )


class ActivityArchiveView(APIView):
    """Archive an activity."""

    permission_classes = [IsActivityManager]

    def post(self, request, activity_id):
        try:
            activity = ActivityService.archive_activity(
                actor=request.user,
                activity_id=activity_id,
            )
        except (DjangoValidationError, DjangoPermissionDenied, PermissionError) as exc:
            _raise_service_error(exc)

        return Response(
            ActivitySerializer(activity).data,
            status=status.HTTP_200_OK,
        )
