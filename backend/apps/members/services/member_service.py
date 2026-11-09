"""
Member business services.

These functions enforce member creation rules.
API permissions are implemented separately.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.members.models import Member
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


PASTOR_ROLE = "PASTOR"
ZONE_LEADER_ROLE = "ZONE_LEADER"


def _has_active_role(user, role_code):
    """Return whether the user has an active, unrevoked role."""
    return user.role_assignments.filter(
        role__code=role_code,
        revoked_at__isnull=True,
    ).exists()


def _require_active_user(user):
    """Require an existing active user."""
    if not isinstance(user, User):
        raise ValidationError("A valid user is required.")

    if not user.is_active:
        raise ValidationError("An inactive user cannot manage members.")


def _require_member_manager(actor):
    """Require an active Pastor or Zone Leader."""
    _require_active_user(actor)

    if not (
        _has_active_role(actor, PASTOR_ROLE)
        or _has_active_role(actor, ZONE_LEADER_ROLE)
    ):
        raise ValidationError(
            "Only an active Pastor or Zone Leader can manage members."
        )


def _require_zone_access(*, zone, actor):
    """
    Require access to an active zone.

    Pastors can access all active zones.
    Zone Leaders can access currently assigned active zones.
    """
    if not isinstance(zone, Zone):
        raise ValidationError("A valid zone is required.")

    if not zone.is_active:
        raise ValidationError("Members cannot be created in an inactive zone.")

    if _has_active_role(actor, PASTOR_ROLE):
        return

    if not _has_active_role(actor, ZONE_LEADER_ROLE):
        raise ValidationError("Only a Pastor or Zone Leader can manage members.")

    now = timezone.now()

    has_assignment = (
        ZoneLeaderAssignment.objects.filter(
            zone=zone,
            user=actor,
            effective_from__lte=now,
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gt=now))
        .exists()
    )

    if not has_assignment:
        raise ValidationError("You are not currently assigned to this zone.")


def _validate_text(value, field_name, max_length=None):
    """Validate and normalize a text field."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")

    value = value.strip()

    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"{field_name} cannot exceed {max_length} characters.")

    return value


def _member_snapshot(member):
    """Return the member fields permitted in audit snapshots."""
    return {
        "id": str(member.id),
        "zone_id": str(member.zone_id),
        "full_name": member.full_name,
        "phone": member.phone,
        "address": member.address,
        "notes": member.notes,
        "is_active": member.is_active,
    }


def create_member(
    *,
    zone,
    full_name,
    actor,
    phone="",
    address="",
    notes="",
):
    """
    Create a member and record its audit event atomically.
    """
    _require_member_manager(actor)
    _require_zone_access(
        zone=zone,
        actor=actor,
    )

    full_name = _validate_text(
        full_name,
        "Full name",
        max_length=200,
    )

    if not full_name:
        raise ValidationError("Full name is required.")

    phone = _validate_text(
        phone,
        "Phone",
        max_length=40,
    )

    address = _validate_text(
        address,
        "Address",
    )

    notes = _validate_text(
        notes,
        "Notes",
    )

    with transaction.atomic():
        member = Member.objects.create(
            zone=zone,
            full_name=full_name,
            phone=phone,
            address=address,
            notes=notes,
            created_by=actor,
        )

        AuditService.record_event(
            actor=actor,
            entity_type="Member",
            entity_id=member.id,
            action=AuditLog.Action.CREATE,
            after_data=_member_snapshot(member),
        )

    return member


_UNSET = object()


def update_member(
    *,
    member,
    actor,
    full_name=_UNSET,
    phone=_UNSET,
    address=_UNSET,
    notes=_UNSET,
    is_active=_UNSET,
):
    """
    Update permitted member fields and record an audit event atomically.

    Zone changes are intentionally excluded. Use the Pastor-only
    transfer service for member transfers.
    """
    _require_member_manager(actor)

    if not isinstance(member, Member) or member.pk is None:
        raise ValidationError("A valid saved member is required.")

    allowed_fields = {
        "full_name": full_name,
        "phone": phone,
        "address": address,
        "notes": notes,
        "is_active": is_active,
    }

    with transaction.atomic():
        current_member = Member.objects.select_for_update().get(pk=member.pk)

        _require_zone_access(
            zone=current_member.zone,
            actor=actor,
        )

        before_data = _member_snapshot(current_member)
        changed_fields = []

        for field_name, value in allowed_fields.items():
            if value is _UNSET:
                continue

            if field_name == "is_active":
                if not isinstance(value, bool):
                    raise ValidationError("Active status must be a boolean.")
            else:
                max_length = (
                    200
                    if field_name == "full_name"
                    else 40 if field_name == "phone" else None
                )

                value = _validate_text(
                    value,
                    field_name.replace("_", " ").title(),
                    max_length=max_length,
                )

                if field_name == "full_name" and not value:
                    raise ValidationError("Full name is required.")

            if getattr(current_member, field_name) != value:
                setattr(current_member, field_name, value)
                changed_fields.append(field_name)

        if not changed_fields:
            return current_member

        current_member.updated_by = actor

        current_member.save(
            update_fields=[
                *changed_fields,
                "updated_by",
                "updated_at",
            ]
        )

        AuditService.record_event(
            actor=actor,
            entity_type="Member",
            entity_id=current_member.id,
            action=AuditLog.Action.UPDATE,
            before_data=before_data,
            after_data=_member_snapshot(current_member),
        )

    return current_member
