"""
Shared media application service for Activities and Announcements.

Enforces manager authorization, draft-only media operations,
parent-row locking, transactional audit logging and storage cleanup.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.activities.models.activity import Activity
from apps.announcements.models.announcement import Announcement
from apps.audit.services.audit_service import AuditService
from apps.content_media.models.content_media import ContentMedia
from apps.content_media.validators import validate_content_media


class MediaService:
    """Business logic for managing Activity and Announcement media."""

    ENTITY_TYPE = "ContentMedia"

    PARENT_MODELS = {
        "activity": Activity,
        "announcement": Announcement,
    }

    @staticmethod
    def _require_media_manager(actor):
        """Require an active authenticated Pastor or Administrator."""

        if (
            actor is None
            or not getattr(actor, "is_authenticated", False)
            or not getattr(actor, "is_active", False)
        ):
            raise PermissionDenied("An active authenticated user is required.")

        has_manager_role = actor.role_assignments.filter(
            revoked_at__isnull=True,
            role__code__in=("PASTOR", "ADMINISTRATOR"),
        ).exists()

        if not has_manager_role:
            raise PermissionDenied(
                "Only Pastors and Administrators may manage content media."
            )

    @staticmethod
    def _get_locked_parent(*, parent_type, parent_id):
        """Retrieve and lock a supported parent content record."""

        model = MediaService.PARENT_MODELS.get(parent_type)

        if model is None:
            raise ValidationError({"parent_type": "Unsupported content type."})

        parent = model.objects.select_for_update().filter(pk=parent_id).first()

        if parent is None:
            raise model.DoesNotExist

        if parent.status != model.Status.DRAFT:
            raise ValidationError(
                "Media can only be modified while content is a draft."
            )

        return parent

    @staticmethod
    def _snapshot(media):
        """Return a JSON-compatible media audit snapshot."""

        return {
            "id": str(media.id),
            "category": media.category,
            "original_filename": media.original_filename,
            "mime_type": media.mime_type,
            "file_size": media.file_size,
            "activity_id": (str(media.activity_id) if media.activity_id else None),
            "announcement_id": (
                str(media.announcement_id) if media.announcement_id else None
            ),
            "uploaded_by": str(media.uploaded_by_id),
        }

    @staticmethod
    def upload_media(
        *,
        actor,
        uploaded_file,
        activity_id=None,
        announcement_id=None,
        correlation_id=None,
    ):
        """
        Upload an attachment to exactly one draft Activity
        or Announcement.

        Storage writes are not transactional. If the database
        operation or audit event fails, the stored file is removed.
        """

        MediaService._require_media_manager(actor)

        if (activity_id is None) == (announcement_id is None):
            raise ValidationError("Specify exactly one Activity or Announcement.")

        if activity_id is not None:
            parent_type = "activity"
            parent_id = activity_id
        else:
            parent_type = "announcement"
            parent_id = announcement_id

        metadata = validate_content_media(uploaded_file)

        media = None

        try:
            with transaction.atomic():
                parent = MediaService._get_locked_parent(
                    parent_type=parent_type,
                    parent_id=parent_id,
                )

                media = ContentMedia(
                    category=metadata["category"],
                    original_filename=metadata["original_filename"],
                    mime_type=metadata["mime_type"],
                    file_size=metadata["file_size"],
                    uploaded_by=actor,
                )

                if parent_type == "activity":
                    media.activity = parent
                else:
                    media.announcement = parent

                media.file = uploaded_file
                media.save()

                AuditService.record_event(
                    actor=actor,
                    entity_type=MediaService.ENTITY_TYPE,
                    entity_id=media.id,
                    action="CREATE",
                    after_data=MediaService._snapshot(media),
                    correlation_id=correlation_id,
                )

            return media

        except Exception:
            # Database rollback does not automatically remove
            # a file already written to the storage backend.
            if media is not None and media.file.name:
                media.file.storage.delete(media.file.name)
            raise

    @staticmethod
    def delete_media(
        *,
        actor,
        media_id,
        correlation_id=None,
    ):
        """
        Delete an attachment belonging to draft content.

        django-cleanup handles physical storage deletion after
        the database transaction commits successfully.
        """

        MediaService._require_media_manager(actor)

        # Read the parent reference first so that parent locking
        # happens before media locking.
        initial_media = ContentMedia.objects.filter(pk=media_id).first()

        if initial_media is None:
            raise ContentMedia.DoesNotExist

        if initial_media.activity_id is not None:
            parent_type = "activity"
            parent_id = initial_media.activity_id
        else:
            parent_type = "announcement"
            parent_id = initial_media.announcement_id

        with transaction.atomic():
            parent = MediaService._get_locked_parent(
                parent_type=parent_type,
                parent_id=parent_id,
            )

            media = ContentMedia.objects.select_for_update().filter(pk=media_id).first()

            if media is None:
                raise ContentMedia.DoesNotExist

            # Recheck the relationship after obtaining the lock.
            if media.activity_id != (
                parent.id if parent_type == "activity" else None
            ) or media.announcement_id != (
                parent.id if parent_type == "announcement" else None
            ):
                raise ValidationError("The media-parent relationship has changed.")

            before_data = MediaService._snapshot(media)

            AuditService.record_event(
                actor=actor,
                entity_type=MediaService.ENTITY_TYPE,
                entity_id=media.id,
                action="UPDATE",
                before_data=before_data,
                after_data={
                    "event": "MEDIA_DELETED",
                    "media_id": str(media.id),
                    "parent_type": parent_type,
                    "parent_id": str(parent.id),
                },
                correlation_id=correlation_id,
            )

            media.delete()

        return media_id
