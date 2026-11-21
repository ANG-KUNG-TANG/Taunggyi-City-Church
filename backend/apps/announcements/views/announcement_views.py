"""
Announcement API views for public access and authorised management.
"""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.announcements.permissions.announcement_permissions import (
    IsAnnouncementManager,
)
from apps.announcements.selectors.announcement_selectors import (
    AnnouncementSelector,
)
from apps.announcements.serializers.announcement_serializer import (
    AnnouncementSerializer,
)
from apps.announcements.services.announcement_service import (
    AnnouncementService,
)
from apps.finance.views.utils import get_correlation_id


class AnnouncementPagination(PageNumberPagination):
    """Bounded page-number pagination for announcement listings."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _raise_service_error(exc):
    """Translate service-layer exceptions into appropriate API errors."""
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail)
    if isinstance(exc, (DjangoPermissionDenied, PermissionError)):
        raise PermissionDenied(str(exc))
    if isinstance(exc, Announcement.DoesNotExist):
        raise NotFound("Announcement not found.")
    raise exc


class PublicAnnouncementListView(APIView):
    """Return published announcements only."""

    permission_classes = [AllowAny]

    def get(self, request):
        announcements = AnnouncementSelector.get_published_announcements()
        paginator = AnnouncementPagination()
        page = paginator.paginate_queryset(announcements, request, view=self)
        serializer = AnnouncementSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PublicAnnouncementDetailView(APIView):
    """Return one published announcement."""

    permission_classes = [AllowAny]

    def get(self, request, announcement_id):
        announcement = AnnouncementSelector.get_published_announcement_by_id(
            announcement_id
        )
        if announcement is None:
            raise NotFound("Published announcement not found.")

        serializer = AnnouncementSerializer(announcement)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnnouncementManagementListView(APIView):
    """List all announcements for authorised managers."""

    permission_classes = [IsAnnouncementManager]

    def get(self, request):
        announcements = AnnouncementSelector.get_all_announcements()
        paginator = AnnouncementPagination()
        page = paginator.paginate_queryset(announcements, request, view=self)
        serializer = AnnouncementSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AnnouncementCreateView(APIView):
    """Create a draft announcement."""

    permission_classes = [IsAnnouncementManager]

    def post(self, request):
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            announcement = AnnouncementService.create_announcement(
                actor=request.user,
                title=serializer.validated_data["title"],
                body=serializer.validated_data["body"],
                correlation_id=get_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )


class AnnouncementManagementDetailView(APIView):
    """Retrieve or update an announcement for authorised managers."""

    permission_classes = [IsAnnouncementManager]

    def get(self, request, announcement_id):
        announcement = AnnouncementSelector.get_announcement_by_id(announcement_id)
        if announcement is None:
            raise NotFound("Announcement not found.")

        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, announcement_id):
        return self._update(request, announcement_id, partial=False)

    def patch(self, request, announcement_id):
        return self._update(request, announcement_id, partial=True)

    def _update(self, request, announcement_id, *, partial):
        announcement = AnnouncementSelector.get_announcement_by_id(announcement_id)
        if announcement is None:
            raise NotFound("Announcement not found.")

        serializer = AnnouncementSerializer(
            announcement,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated_announcement = AnnouncementService.update_announcement(
                actor=request.user,
                announcement_id=announcement_id,
                title=serializer.validated_data.get("title", announcement.title),
                body=serializer.validated_data.get("body", announcement.body),
                correlation_id=get_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
            Announcement.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AnnouncementSerializer(updated_announcement).data,
            status=status.HTTP_200_OK,
        )


class AnnouncementPublishView(APIView):
    """Publish an announcement with server-side authorization."""

    permission_classes = [IsAnnouncementManager]

    def post(self, request, announcement_id):
        try:
            announcement = AnnouncementService.publish_announcement(
                actor=request.user,
                announcement_id=announcement_id,
                correlation_id=get_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
            Announcement.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK,
        )


class AnnouncementArchiveView(APIView):
    """Archive an announcement."""

    permission_classes = [IsAnnouncementManager]

    def post(self, request, announcement_id):
        try:
            announcement = AnnouncementService.archive_announcement(
                actor=request.user,
                announcement_id=announcement_id,
                correlation_id=get_correlation_id(request),
            )
        except (
            DjangoValidationError,
            DjangoPermissionDenied,
            PermissionError,
            Announcement.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)

        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK,
        )


from apps.announcements.models.announcement import Announcement
