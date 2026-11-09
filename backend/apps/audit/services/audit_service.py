"""
Audit service for recording sensitive system operations.

Audit records are created through this service and should be written
inside the same transaction as the domain operation being audited.
"""

from uuid import UUID

from django.core.exceptions import ValidationError

from apps.audit.models.audit_log import AuditLog


# Fields that must never be included in audit snapshots.
SENSITIVE_FIELDS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
}


def _clean_snapshot(data):
    """
    Return a safe snapshot containing JSON-compatible values.

    Sensitive fields are excluded recursively.
    """
    if data is None:
        return None

    if not isinstance(data, dict):
        raise ValidationError("Audit snapshots must be dictionaries or None.")

    cleaned = {}

    for key, value in data.items():
        normalized_key = str(key).lower()

        if normalized_key in SENSITIVE_FIELDS:
            continue

        if isinstance(value, dict):
            cleaned[key] = _clean_snapshot(value)

        elif isinstance(value, (list, tuple)):
            cleaned[key] = [
                _clean_snapshot(item) if isinstance(item, dict) else item
                for item in value
            ]

        elif isinstance(value, UUID):
            cleaned[key] = str(value)

        else:
            cleaned[key] = value

    return cleaned


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
            actor: Authenticated user responsible for the operation.
            entity_type: Domain entity name, e.g. "Member".
            entity_id: UUID of the affected entity.
            action: AuditLog.Action value.
            before_data: Optional previous-state snapshot.
            after_data: Optional resulting-state snapshot.
            correlation_id: Optional request correlation UUID.

        Returns:
            The newly created AuditLog instance.
        """
        if not entity_type or len(entity_type) > 80:
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
