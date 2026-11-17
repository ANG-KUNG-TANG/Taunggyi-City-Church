"""
Business logic for staff account management.

All staff account operations require an active Administrator role.
Account creation, updates, and deactivation are audited.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Subquery

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.audit.services.audit_service import AuditService


User = get_user_model()

STAFF_PROFILE_FIELDS = {
    "email",
    "first_name",
    "last_name",
}

AUDIT_ENTITY_TYPE = "StaffAccount"


def _require_administrator(actor):
    """Require an authenticated user with an active Administrator role."""

    if not actor or not actor.is_authenticated:
        raise PermissionDenied("Authentication is required.")

    if not actor.is_active:
        raise PermissionDenied("Inactive accounts cannot perform this operation.")

    has_administrator_role = actor.role_assignments.filter(
        revoked_at__isnull=True,
        role__code="ADMINISTRATOR",
    ).exists()

    if not has_administrator_role:
        raise PermissionDenied("Only Administrators can manage staff accounts.")


def _account_snapshot(user):
    """Return an explicitly whitelisted account snapshot."""

    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
    }


def _validate_profile_changes(changes):
    """Reject fields outside the permitted staff profile."""

    if not isinstance(changes, dict):
        raise ValidationError("Account changes must be provided as a dictionary.")

    unexpected_fields = set(changes) - STAFF_PROFILE_FIELDS

    if unexpected_fields:
        raise ValidationError(
            "Unsupported account fields: " + ", ".join(sorted(unexpected_fields))
        )

    if not changes:
        raise ValidationError("At least one account field must be provided.")


@transaction.atomic
def create_staff_account(*, actor, validated_data):
    """
    Create a staff account with an unusable password.

    Role assignment and password setup are separate operations.
    """

    _require_administrator(actor)

    if not isinstance(validated_data, dict):
        raise ValidationError("Account data must be a dictionary.")

    unexpected_fields = set(validated_data) - STAFF_PROFILE_FIELDS

    if unexpected_fields:
        raise ValidationError(
            "Unsupported account fields: " + ", ".join(sorted(unexpected_fields))
        )

    if not validated_data.get("email"):
        raise ValidationError("An email address is required.")

    account = User.objects.create_user(**validated_data)

    AuditService.record_event(
        actor=actor,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=account.pk,
        action="CREATE",
        after_data=_account_snapshot(account),
    )

    return account


def list_staff_accounts(*, actor):
    """Return staff accounts after verifying Administrator permission."""

    _require_administrator(actor)

    return User.objects.all()


def get_staff_account(*, actor, user_id):
    """Retrieve an individual staff account."""

    _require_administrator(actor)

    return User.objects.get(pk=user_id)


@transaction.atomic
def update_staff_account(*, actor, user_id, changes):
    """
    Update permitted staff profile fields.

    Account activation status is deliberately excluded because
    deactivation has additional security requirements.
    """

    _require_administrator(actor)
    _validate_profile_changes(changes)

    account = User.objects.select_for_update().get(pk=user_id)

    if not account.is_active:
        raise ValidationError(
            "Inactive accounts cannot be updated through this operation."
        )

    before_data = _account_snapshot(account)

    changed_fields = []

    for field, value in changes.items():
        if getattr(account, field) != value:
            setattr(account, field, value)
            changed_fields.append(field)

    if not changed_fields:
        return account

    account.save(update_fields=changed_fields)

    AuditService.record_event(
        actor=actor,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=account.pk,
        action="UPDATE",
        before_data=before_data,
        after_data=_account_snapshot(account),
    )

    return account


@transaction.atomic
def deactivate_staff_account(*, actor, user_id):
    """
    Deactivate a staff account without deleting its history.

    Administrator deactivation is serialised through the Administrator
    role row. Active Administrator assignments and account rows are
    locked before the final authorization and invariant checks.
    """

    _require_administrator(actor)

    if str(actor.pk) == str(user_id):
        raise PermissionDenied("Administrators cannot deactivate their own accounts.")

    # Use the Administrator role row as a transaction-wide mutex.
    administrator_role = Role.objects.select_for_update().get(code="ADMINISTRATOR")

    # Lock current active Administrator assignments. This also prevents
    # concurrent revocation of these existing assignments while we decide.
    active_assignments = list(
        UserRole.objects.select_for_update()
        .filter(
            role=administrator_role,
            revoked_at__isnull=True,
            user__is_active=True,
        )
        .order_by("user_id", "pk")
    )

    # Lock relevant user rows in a consistent order.
    user_ids_to_lock = {assignment.user_id for assignment in active_assignments}
    user_ids_to_lock.update((actor.pk, user_id))

    locked_users = {
        user.pk: user
        for user in User.objects.select_for_update()
        .filter(pk__in=user_ids_to_lock)
        .order_by("pk")
    }

    # Revalidate the actor using database state after acquiring locks.
    locked_actor = locked_users.get(actor.pk)

    if locked_actor is None or not locked_actor.is_active:
        raise PermissionDenied("Inactive accounts cannot perform this operation.")

    if not UserRole.objects.filter(
        user=locked_actor,
        role=administrator_role,
        revoked_at__isnull=True,
    ).exists():
        raise PermissionDenied("Only Administrators can manage staff accounts.")

    # Re-query after the locks have been acquired. Under PostgreSQL's
    # READ COMMITTED isolation, this statement sees newly committed state.
    active_administrator_ids = set(
        UserRole.objects.filter(
            role=administrator_role,
            revoked_at__isnull=True,
            user__is_active=True,
        ).values_list("user_id", flat=True)
    )

    account = locked_users.get(user_id)

    if account is None:
        raise User.DoesNotExist

    if not account.is_active:
        raise ValidationError("This account is already inactive.")

    if account.pk in active_administrator_ids:
        if len(active_administrator_ids) <= 1:
            raise PermissionDenied(
                "The last active Administrator cannot be deactivated."
            )

    before_data = _account_snapshot(account)

    account.is_active = False
    account.save(update_fields=["is_active"])

    AuditService.record_event(
        actor=locked_actor,
        entity_type=AUDIT_ENTITY_TYPE,
        entity_id=account.pk,
        action="UPDATE",
        before_data=before_data,
        after_data=_account_snapshot(account),
    )

    return account
