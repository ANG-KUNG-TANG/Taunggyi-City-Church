"""
Zone business services.

These functions enforce zone-management, assignment, and audit rules.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


PASTOR_ROLE = "PASTOR"
ZONE_LEADER_ROLE = "ZONE_LEADER"


def _has_active_role(user, role_code):
    """Return whether the user has an active assignment to a role."""
    return user.role_assignments.filter(
        role__code=role_code,
        revoked_at__isnull=True,
    ).exists()


def _require_active_user(user, message):
    """Require an existing active user."""
    if not isinstance(user, User):
        raise ValidationError("A valid user is required.")

    if not user.is_active:
        raise ValidationError(message)


def _require_pastor(actor):
    """Require an active Pastor to manage zones and assignments."""
    _require_active_user(
        actor,
        "An inactive user cannot manage zones.",
    )

    if not _has_active_role(actor, PASTOR_ROLE):
        raise ValidationError("Only an active Pastor can manage zones and assignments.")


def _validate_zone_name(name):
    """Normalize and validate a zone name."""
    if not isinstance(name, str):
        raise ValidationError("Zone name must be a string.")

    name = name.strip()

    if not name:
        raise ValidationError("Zone name is required.")

    if len(name) > 100:
        raise ValidationError("Zone name cannot exceed 100 characters.")

    return name


def _zone_snapshot(zone):
    """Return a JSON-serializable zone snapshot."""
    return {
        "name": zone.name,
        "description": zone.description,
        "is_active": zone.is_active,
    }


def _assignment_snapshot(assignment):
    """Return a JSON-serializable assignment snapshot."""
    return {
        "zone_id": str(assignment.zone_id),
        "user_id": str(assignment.user_id),
        "assigned_by_id": str(assignment.assigned_by_id),
        "effective_from": assignment.effective_from.isoformat(),
        "effective_to": (
            assignment.effective_to.isoformat() if assignment.effective_to else None
        ),
    }


def create_zone(*, name, actor, description=""):
    """Create a zone and record its audit event."""
    _require_pastor(actor)

    name = _validate_zone_name(name)

    if not isinstance(description, str):
        raise ValidationError("Description must be a string.")

    description = description.strip()

    with transaction.atomic():
        if Zone.objects.filter(name__iexact=name).exists():
            raise ValidationError("A zone with this name already exists.")

        zone = Zone.objects.create(
            name=name,
            description=description,
        )

        AuditService.record_event(
            actor=actor,
            entity_type="Zone",
            entity_id=zone.pk,
            action=AuditLog.Action.CREATE,
            after_data=_zone_snapshot(zone),
        )

    return zone


def update_zone(*, zone, actor, name=None, description=None):
    """Update a zone and record before-and-after snapshots."""
    _require_pastor(actor)

    if not isinstance(zone, Zone):
        raise ValidationError("A valid zone is required.")

    with transaction.atomic():
        zone = Zone.objects.select_for_update().get(pk=zone.pk)

        before_data = _zone_snapshot(zone)

        if name is not None:
            zone.name = _validate_zone_name(name)

        if description is not None:
            if not isinstance(description, str):
                raise ValidationError("Description must be a string.")

            zone.description = description.strip()

        duplicate = (
            Zone.objects.filter(name__iexact=zone.name).exclude(pk=zone.pk).exists()
        )

        if duplicate:
            raise ValidationError("A zone with this name already exists.")

        zone.save(update_fields=["name", "description", "updated_at"])

        AuditService.record_event(
            actor=actor,
            entity_type="Zone",
            entity_id=zone.pk,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=_zone_snapshot(zone),
        )

    return zone


def deactivate_zone(*, zone, actor):
    """Deactivate a zone without deleting it."""
    _require_pastor(actor)

    if not isinstance(zone, Zone):
        raise ValidationError("A valid zone is required.")

    with transaction.atomic():
        zone = Zone.objects.select_for_update().get(pk=zone.pk)

        if zone.is_active:
            before_data = _zone_snapshot(zone)

            zone.is_active = False
            zone.save(update_fields=["is_active", "updated_at"])

            AuditService.record_event(
                actor=actor,
                entity_type="Zone",
                entity_id=zone.pk,
                action=AuditLog.Action.UPDATE,
                before_data=before_data,
                after_data=_zone_snapshot(zone),
            )

    return zone


def assign_zone_leader(
    *,
    zone,
    user,
    actor,
    effective_from=None,
):
    """
    Assign an active Zone Leader to an active zone.

    Multiple leaders may be assigned to one zone.
    One leader may serve multiple zones.
    """
    _require_pastor(actor)

    if not isinstance(zone, Zone):
        raise ValidationError("A valid zone is required.")

    _require_active_user(
        user,
        "An inactive user cannot be assigned as a Zone Leader.",
    )

    if not _has_active_role(user, ZONE_LEADER_ROLE):
        raise ValidationError("The user must have an active ZONE_LEADER role.")

    if effective_from is None:
        effective_from = timezone.now()

    if not timezone.is_aware(effective_from):
        raise ValidationError("effective_from must be a valid datetime.")

    try:
        with transaction.atomic():
            # Lock the zone to coordinate with concurrent deactivation.
            locked_zone = Zone.objects.select_for_update().get(pk=zone.pk)

            if not locked_zone.is_active:
                raise ValidationError(
                    "An inactive zone cannot receive new assignments."
                )

            if ZoneLeaderAssignment.objects.filter(
                zone=locked_zone,
                user=user,
                effective_to__isnull=True,
            ).exists():
                raise ValidationError(
                    "This user already has an active assignment " "to this zone."
                )

            assignment = ZoneLeaderAssignment.objects.create(
                zone=locked_zone,
                user=user,
                assigned_by=actor,
                effective_from=effective_from,
            )

            AuditService.record_event(
                actor=actor,
                entity_type="ZoneLeaderAssignment",
                entity_id=assignment.pk,
                action=AuditLog.Action.CREATE,
                after_data=_assignment_snapshot(assignment),
            )

    except IntegrityError as exc:
        raise ValidationError(
            "An active assignment already exists for this zone and user."
        ) from exc

    return assignment


def end_zone_leader_assignment(
    *,
    assignment,
    actor,
    effective_to=None,
):
    """End an assignment while preserving its history."""
    _require_pastor(actor)

    if not isinstance(assignment, ZoneLeaderAssignment):
        raise ValidationError("A valid Zone Leader assignment is required.")

    if effective_to is None:
        effective_to = timezone.now()

    if not timezone.is_aware(effective_to):
        raise ValidationError("effective_to must be a valid datetime.")

    with transaction.atomic():
        assignment = ZoneLeaderAssignment.objects.select_for_update().get(
            pk=assignment.pk
        )

        if assignment.effective_to is not None:
            raise ValidationError("This assignment has already ended.")

        if effective_to < assignment.effective_from:
            raise ValidationError("Assignment end time cannot precede its start time.")

        before_data = _assignment_snapshot(assignment)

        assignment.effective_to = effective_to
        assignment.save(update_fields=["effective_to"])

        AuditService.record_event(
            actor=actor,
            entity_type="ZoneLeaderAssignment",
            entity_id=assignment.pk,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=_assignment_snapshot(assignment),
        )

    return assignment
