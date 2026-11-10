"""
Activity service for the Taunggyi City Church system.

Handles activity creation, editing, publication, and archiving.
Sensitive operations are recorded in the audit log.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.activities.models.activity import Activity
from apps.audit.services.audit_service import AuditService


class ActivityService:
    """Business logic for managing church activities."""

    ENTITY_TYPE = "Activity"

    @staticmethod
    def _validate_content(*, title, body):
        if not isinstance(title, str) or not title.strip():
            raise ValidationError({"title": "Title is required."})

        if len(title.strip()) > 200:
            raise ValidationError({"title": "Title must not exceed 200 characters."})

        if not isinstance(body, str) or not body.strip():
            raise ValidationError({"body": "Body is required."})

    @staticmethod
    def _snapshot(activity):
        return {
            "id": str(activity.id),
            "title": activity.title,
            "body": activity.body,
            "status": activity.status,
            "published_by": (
                str(activity.published_by_id) if activity.published_by_id else None
            ),
            "published_at": (
                activity.published_at.isoformat() if activity.published_at else None
            ),
        }

    @staticmethod
    @transaction.atomic
    def create_activity(*, actor, title, body, correlation_id=None):
        """Create a new activity as a draft."""

        ActivityService._validate_content(title=title, body=body)

        activity = Activity.objects.create(
            title=title.strip(),
            body=body.strip(),
            status=Activity.Status.DRAFT,
        )

        AuditService.record_event(
            actor=actor,
            entity_type=ActivityService.ENTITY_TYPE,
            entity_id=activity.id,
            action="CREATE",
            after_data=ActivityService._snapshot(activity),
            correlation_id=correlation_id,
        )

        return activity

    @staticmethod
    @transaction.atomic
    def update_activity(
        *,
        actor,
        activity_id,
        title,
        body,
        correlation_id=None,
    ):
        """Update activity content without changing its publication state."""

        ActivityService._validate_content(title=title, body=body)

        activity = Activity.objects.select_for_update().get(id=activity_id)

        if activity.status == Activity.Status.ARCHIVED:
            raise ValidationError("Archived activities cannot be edited.")

        before_data = ActivityService._snapshot(activity)

        activity.title = title.strip()
        activity.body = body.strip()
        activity.save(update_fields=["title", "body", "updated_at"])

        AuditService.record_event(
            actor=actor,
            entity_type=ActivityService.ENTITY_TYPE,
            entity_id=activity.id,
            action="UPDATE",
            before_data=before_data,
            after_data=ActivityService._snapshot(activity),
            correlation_id=correlation_id,
        )

        return activity

    @staticmethod
    @transaction.atomic
    def publish_activity(*, actor, activity_id, correlation_id=None):
        """Publish an activity after server-side role authorization."""

        activity = Activity.objects.select_for_update().get(id=activity_id)

        if not actor or not actor.is_authenticated or not actor.is_active:
            raise ValidationError("An active authenticated user is required.")

        has_publish_role = actor.role_assignments.filter(
            revoked_at__isnull=True,
            role__code__in=["PASTOR", "ADMINISTRATOR"],
        ).exists()

        if not has_publish_role:
            raise PermissionError(
                "Only Pastors and Administrators may publish activities."
            )

        ActivityService._validate_content(
            title=activity.title,
            body=activity.body,
        )

        if activity.status == Activity.Status.ARCHIVED:
            raise ValidationError("Archived activities cannot be published.")

        before_data = ActivityService._snapshot(activity)

        activity.status = Activity.Status.PUBLISHED
        activity.published_by = actor
        activity.published_at = timezone.now()
        activity.save(
            update_fields=[
                "status",
                "published_by",
                "published_at",
                "updated_at",
            ]
        )

        AuditService.record_event(
            actor=actor,
            entity_type=ActivityService.ENTITY_TYPE,
            entity_id=activity.id,
            action="PUBLISH",
            before_data=before_data,
            after_data=ActivityService._snapshot(activity),
            correlation_id=correlation_id,
        )

        return activity

    @staticmethod
    @transaction.atomic
    def archive_activity(*, actor, activity_id, correlation_id=None):
        """Archive an activity and record the change."""

        activity = Activity.objects.select_for_update().get(id=activity_id)

        before_data = ActivityService._snapshot(activity)

        activity.status = Activity.Status.ARCHIVED
        activity.save(update_fields=["status", "updated_at"])

        AuditService.record_event(
            actor=actor,
            entity_type=ActivityService.ENTITY_TYPE,
            entity_id=activity.id,
            action="UPDATE",
            before_data=before_data,
            after_data=ActivityService._snapshot(activity),
            correlation_id=correlation_id,
        )

        return activity
