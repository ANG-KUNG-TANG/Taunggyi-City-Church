"""Serializers for financial audit-history queries and responses."""

from rest_framework import serializers

from apps.audit.models.audit_log import AuditLog
from apps.audit.selectors.audit_selectors import FINANCIAL_ENTITY_TYPES


class FinancialAuditHistoryQuerySerializer(serializers.Serializer):
    """Validate optional financial audit-history filters."""

    entity_type = serializers.ChoiceField(
        choices=[(value, value) for value in FINANCIAL_ENTITY_TYPES],
        required=False,
    )
    entity_id = serializers.UUIDField(required=False)
    actor_id = serializers.UUIDField(required=False)
    action = serializers.ChoiceField(
        choices=AuditLog.Action.choices,
        required=False,
    )
    correlation_id = serializers.UUIDField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "start_date must not be later than end_date."
            )

        return attrs


class FinancialAuditHistoryReadSerializer(serializers.ModelSerializer):
    """Read-only representation of a financial audit event."""

    actor_id = serializers.UUIDField(read_only=True, allow_null=True)
    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_id",
            "actor_email",
            "entity_type",
            "entity_id",
            "action",
            "before_data",
            "after_data",
            "occurred_at",
            "correlation_id",
        ]
        read_only_fields = fields
