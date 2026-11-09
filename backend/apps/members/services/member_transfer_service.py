"""
Pastor-only member transfer service.

Transfers update a member's current zone and record an audit event
within the same database transaction.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.members.models import Member
from apps.members.services.member_service import (
    PASTOR_ROLE,
    _has_active_role,
    _member_snapshot,
)
from apps.zones.models.zones import Zone


def transfer_member(*, member, destination_zone, actor):
    """
    Transfer a member to another active zone.

    Only an active Pastor may perform this operation.
    The member update and audit event are atomic.
    """
    if not isinstance(actor, User):
        raise ValidationError("A valid user is required.")

    if not actor.is_active:
        raise ValidationError("An inactive user cannot transfer members.")

    if not _has_active_role(actor, PASTOR_ROLE):
        raise ValidationError("Only an active Pastor can transfer members.")

    if not isinstance(member, Member) or member.pk is None:
        raise ValidationError("A valid saved member is required.")

    if not isinstance(destination_zone, Zone):
        raise ValidationError("A valid destination zone is required.")

    with transaction.atomic():
        current_member = Member.objects.select_for_update().get(pk=member.pk)

        target_zone = Zone.objects.select_for_update().get(pk=destination_zone.pk)

        if not target_zone.is_active:
            raise ValidationError("Members cannot be transferred to an inactive zone.")

        if current_member.zone_id == target_zone.id:
            raise ValidationError("The member already belongs to this zone.")

        before_data = _member_snapshot(current_member)

        current_member.zone = target_zone
        current_member.updated_by = actor

        current_member.save(
            update_fields=[
                "zone",
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
