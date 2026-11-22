from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.http import FileResponse
from django.utils.http import content_disposition_header

from rest_framework import status
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions.role_permission import IsPastorOrAdministrator
from apps.activities.models.activity import Activity
from apps.announcements.models.announcement import Announcement
from apps.content_media.models.content_media import ContentMedia
from apps.content_media.serializers import (
    ContentMediaSerializer,
    ContentMediaUploadSerializer,
)
from apps.content_media.services import MediaService
from apps.finance.views.utils import get_correlation_id


def _raise_service_error(exc):
    """Translate service-layer exceptions into DRF responses."""

    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        raise ValidationError(detail)

    if isinstance(exc, DjangoPermissionDenied):
        raise PermissionDenied(str(exc))

    if isinstance(exc, PermissionError):
        raise PermissionDenied(str(exc))

    if isinstance(
        exc,
        (
            Activity.DoesNotExist,
            Announcement.DoesNotExist,
            ContentMedia.DoesNotExist,
        ),
    ):
        raise NotFound("The requested resource was not found.")

    raise exc


class ParentMediaListUploadView(APIView):
    """
    List and upload media belonging to an Activity or Announcement.

    Only Pastor and Administrator roles can access this endpoint.
    Uploads are restricted to draft parents by MediaService.
    """

    permission_classes = [IsPastorOrAdministrator]
    parser_classes = [MultiPartParser, FormParser]

    parent_type = None
    parent_model = None
    parent_id_kwarg = "parent_id"

    def get_parent(self):
        parent_id = self.kwargs[self.parent_id_kwarg]

        try:
            return self.parent_model.objects.get(pk=parent_id)
        except self.parent_model.DoesNotExist:
            raise NotFound("The requested content was not found.")

    def get(self, request, *args, **kwargs):
        parent = self.get_parent()

        filters = {
            self.parent_type: parent,
        }

        media_items = ContentMedia.objects.filter(**filters)

        serializer = ContentMediaSerializer(
            media_items,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        parent = self.get_parent()

        serializer = ContentMediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            correlation_id = get_correlation_id(request)

            media = MediaService.upload_media(
                actor=request.user,
                uploaded_file=serializer.validated_data["file"],
                correlation_id=correlation_id,
                **{
                    f"{self.parent_type}_id": parent.pk,
                },
            )
        except Exception as exc:
            _raise_service_error(exc)

        response_serializer = ContentMediaSerializer(
            media,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ActivityMediaListUploadView(ParentMediaListUploadView):
    parent_type = "activity"
    parent_model = Activity
    parent_id_kwarg = "activity_id"


class AnnouncementMediaListUploadView(ParentMediaListUploadView):
    parent_type = "announcement"
    parent_model = Announcement
    parent_id_kwarg = "announcement_id"


class MediaDeleteView(APIView):
    """Delete media associated with draft content."""

    permission_classes = [IsPastorOrAdministrator]

    def delete(self, request, media_id, *args, **kwargs):
        try:
            MediaService.delete_media(
                actor=request.user,
                media_id=media_id,
                correlation_id=get_correlation_id(request),
            )
        except Exception as exc:
            _raise_service_error(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class MediaFileView(APIView):
    """
    Securely stream a media file.

    Published content media is publicly accessible.
    Unpublished or archived content media requires an active
    Pastor or Administrator role.
    """

    permission_classes = [AllowAny]

    def get(self, request, media_id, *args, **kwargs):
        try:
            media = ContentMedia.objects.select_related("activity", "announcement").get(
                pk=media_id
            )
        except ContentMedia.DoesNotExist:
            raise NotFound("The requested media was not found.")

        parent = media.activity or media.announcement

        if parent is None:
            raise NotFound("The requested media was not found.")

        published_status = (
            Activity.Status.PUBLISHED
            if media.activity_id
            else Announcement.Status.PUBLISHED
        )

        is_published = parent.status == published_status

        if not is_published:
            user = request.user

            if not user or not user.is_authenticated:
                raise NotAuthenticated(
                    "Authentication is required to access this media."
                )

            if not IsPastorOrAdministrator().has_permission(
                request,
                self,
            ):
                raise PermissionDenied(
                    "You do not have permission to access this media."
                )

        try:
            file_handle = media.file.open("rb")
        except (FileNotFoundError, OSError, ValueError):
            raise NotFound("The requested media file is unavailable.")

        response = FileResponse(
            file_handle,
            content_type=media.mime_type,
        )

        response["Cache-Control"] = "private, no-store"
        response["Content-Disposition"] = content_disposition_header(
            True,
            media.original_filename,
        )
        response["X-Content-Type-Options"] = "nosniff"

        return response
