"""
Audit service for recording sensitive system operations.

Audit records are created through this service and should be written
inside the same transaction as the domain operation being audited.
"""

import math
import re
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.audit.models.audit_log import AuditLog


# Credential-related fields are excluded from audit snapshots.
SENSITIVE_FIELD_FRAGMENTS = (
    "password",
    "token",
    "secret",
    "authorization",
    "credential",
    "cookie",
    "privatekey",
    "apikey",
    "sessionkey",
)


def _normalize_key(key):
    """Normalise field names to catch spelling and separator variations."""
    return re.sub(r"[^a-z0-9]", "", str(key).casefold())


def _is_sensitive_field(key):
    normalized_key = _normalize_key(key)
    return any(fragment in normalized_key for fragment in SENSITIVE_FIELD_FRAGMENTS)


def _clean_value(value):
    """
    Recursively sanitise and validate a snapshot value.

    Supported values are JSON primitives, UUIDs, dictionaries,
    lists, and tuples. Tuples are converted to lists.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("Audit snapshots cannot contain non-finite numbers.")
        return value

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, dict):
        cleaned = {}

        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValidationError("Audit snapshot dictionary keys must be strings.")

            if _is_sensitive_field(key):
                continue

            cleaned[key] = _clean_value(nested_value)

        return cleaned

    if isinstance(value, (list, tuple)):
        return [_clean_value(item) for item in value]

    raise ValidationError(
        "Audit snapshots contain an unsupported value type: " f"{type(value).__name__}."
    )


def _clean_snapshot(data):
    """
    Return a safe, JSON-compatible dictionary snapshot or None.
    """
    if data is None:
        return None

    if not isinstance(data, dict):
        raise ValidationError("Audit snapshots must be dictionaries or None.")

    return _clean_value(data)


def _validate_actor(actor):
    """
    Accept None for legitimate system events.

    Otherwise, require a persisted instance of the configured user model.
    """
    if actor is None:
        return

    User = get_user_model()

    if not isinstance(actor, User):
        raise ValidationError(
            "Audit actor must be an instance of the configured user model."
        )

    if actor.pk is None or actor._state.adding:
        raise ValidationError("Audit actor must be a persisted user.")

    if not User._default_manager.filter(pk=actor.pk).exists():
        raise ValidationError("Audit actor does not exist.")


class AuditService:
    """
    Central service for creating immutable audit events.
    """

    @staticmethod
    def record_event(
        *,
        actor,
        entity_type,
        entity_id,
        action,
        before_data=None,
        after_data=None,
        correlation_id=None,
    ):
        """
        Create an audit event.

        Args:
            actor: Authenticated user responsible for the operation,
                or None for a legitimate system-generated event.
            entity_type: Domain entity name, e.g. "Member".
            entity_id: UUID of the affected entity.
            action: AuditLog.Action value.
            before_data: Optional previous-state snapshot.
            after_data: Optional resulting-state snapshot.
            correlation_id: Optional request correlation UUID.

        Returns:
            The newly created AuditLog instance.
        """
        if not isinstance(entity_type, str) or not entity_type.strip():
            raise ValidationError(
                "entity_type must contain between 1 and 80 characters."
            )

        if len(entity_type) > 80:
            raise ValidationError(
                "entity_type must contain between 1 and 80 characters."
            )

        if not isinstance(entity_id, UUID):
            raise ValidationError("entity_id must be a UUID.")

        if correlation_id is not None and not isinstance(correlation_id, UUID):
            raise ValidationError("correlation_id must be a UUID or None.")

        valid_actions = {choice[0] for choice in AuditLog.Action.choices}

        if action not in valid_actions:
            raise ValidationError("Invalid audit action.")

        _validate_actor(actor)

        safe_before = _clean_snapshot(before_data)
        safe_after = _clean_snapshot(after_data)

        return AuditLog.objects.create(
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_data=safe_before,
            after_data=safe_after,
            correlation_id=correlation_id,
        )
