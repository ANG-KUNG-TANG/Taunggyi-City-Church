"""
Announcement application service for the Taunggyi City Church system.

Handles announcement creation, editing, publication, and archiving.
Sensitive operations and their audit events are transactional.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.announcements.models.announcement import Announcement
from apps.announcements.validators import validate_announcement_content
from apps.audit.services.audit_service import AuditService


class AnnouncementService:
    """Business logic for managing church announcements."""

    ENTITY_TYPE = "Announcement"

    @staticmethod
    def _snapshot(announcement):
        """Return a JSON-compatible announcement snapshot."""
        return {
            "id": str(announcement.id),
            "title": announcement.title,
            "body": announcement.body,
            "status": announcement.status,
            "published_by": (
                str(announcement.published_by_id)
                if announcement.published_by_id
                else None
            ),
            "published_at": (
                announcement.published_at.isoformat()
                if announcement.published_at
                else None
            ),
        }

    @staticmethod
    def _require_announcement_manager(actor):
        """Require an active Pastor or Administrator."""
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
                "Only Pastors and Administrators may manage announcements."
            )

    @staticmethod
    @transaction.atomic
    def create_announcement(
        *,
        actor,
        title,
        body,
        correlation_id=None,
    ):
        """Create a new announcement as a draft."""
        AnnouncementService._require_announcement_manager(actor)

        content = validate_announcement_content(
            title=title,
            body=body,
        )

        announcement = Announcement.objects.create(
            title=content["title"],
            body=content["body"],
            status=Announcement.Status.DRAFT,
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AnnouncementService.ENTITY_TYPE,
            entity_id=announcement.id,
            action="CREATE",
            after_data=AnnouncementService._snapshot(announcement),
            correlation_id=correlation_id,
        )

        return announcement

    @staticmethod
    @transaction.atomic
    def update_announcement(
        *,
        actor,
        announcement_id,
        title=None,
        body=None,
        correlation_id=None,
    ):
        """Update announcement content without changing its publication state."""
        AnnouncementService._require_announcement_manager(actor)

        announcement = (
            Announcement.objects.select_for_update().filter(id=announcement_id).first()
        )

        if announcement is None:
            raise Announcement.DoesNotExist

        if announcement.status == Announcement.Status.ARCHIVED:
            raise ValidationError("Archived announcements cannot be edited.")

        content = validate_announcement_content(
            title=(title if title is not None else announcement.title),
            body=(body if body is not None else announcement.body),
        )

        if (
            announcement.title == content["title"]
            and announcement.body == content["body"]
        ):
            return announcement

        before_data = AnnouncementService._snapshot(announcement)

        announcement.title = content["title"]
        announcement.body = content["body"]
        announcement.save(update_fields=["title", "body", "updated_at"])

        AuditService.record_event(
            actor=actor,
            entity_type=AnnouncementService.ENTITY_TYPE,
            entity_id=announcement.id,
            action="UPDATE",
            before_data=before_data,
            after_data=AnnouncementService._snapshot(announcement),
            correlation_id=correlation_id,
        )

        return announcement

    @staticmethod
    @transaction.atomic
    def publish_announcement(
        *,
        actor,
        announcement_id,
        correlation_id=None,
    ):
        """Publish an announcement after server-side authorization."""
        AnnouncementService._require_announcement_manager(actor)

        announcement = (
            Announcement.objects.select_for_update().filter(id=announcement_id).first()
        )

        if announcement is None:
            raise Announcement.DoesNotExist

        if announcement.status == Announcement.Status.ARCHIVED:
            raise ValidationError("Archived announcements cannot be published.")

        if announcement.status == Announcement.Status.PUBLISHED:
            raise ValidationError("This announcement is already published.")

        validate_announcement_content(
            title=announcement.title,
            body=announcement.body,
        )

        before_data = AnnouncementService._snapshot(announcement)

        announcement.status = Announcement.Status.PUBLISHED
        announcement.published_by = actor
        announcement.published_at = timezone.now()
        announcement.save(
            update_fields=[
                "status",
                "published_by",
                "published_at",
                "updated_at",
            ]
        )

        AuditService.record_event(
            actor=actor,
            entity_type=AnnouncementService.ENTITY_TYPE,
            entity_id=announcement.id,
            action="PUBLISH",
            before_data=before_data,
            after_data=AnnouncementService._snapshot(announcement),
            correlation_id=correlation_id,
        )

        return announcement

    @staticmethod
    @transaction.atomic
    def archive_announcement(
        *,
        actor,
        announcement_id,
        correlation_id=None,
    ):
        """Archive an announcement and record its state transition."""
        AnnouncementService._require_announcement_manager(actor)

        announcement = (
            Announcement.objects.select_for_update().filter(id=announcement_id).first()
        )

        if announcement is None:
            raise Announcement.DoesNotExist

        if announcement.status == Announcement.Status.ARCHIVED:
            raise ValidationError("This announcement is already archived.")

        before_data = AnnouncementService._snapshot(announcement)

        announcement.status = Announcement.Status.ARCHIVED
        announcement.save(update_fields=["status", "updated_at"])

        AuditService.record_event(
            actor=actor,
            entity_type=AnnouncementService.ENTITY_TYPE,
            entity_id=announcement.id,
            action="UPDATE",
            before_data=before_data,
            after_data=AnnouncementService._snapshot(announcement),
            correlation_id=correlation_id,
        )

        return announcement
