"""Serializers for financial authorisation requests and responses."""

from rest_framework import serializers

from apps.finance.models.financial_authorization import (
    FinancialAuthorization,
)


class FinancialAuthorizationRequestSerializer(serializers.Serializer):
    """Validate a financial authorisation decision."""

    decision = serializers.ChoiceField(
        choices=FinancialAuthorization.Decision.choices,
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    correlation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    def validate_reason(self, value):
        if value is None:
            return value
        return value.strip()

    def validate(self, attrs):
        decision = attrs["decision"]
        reason = attrs.get("reason")

        if decision == FinancialAuthorization.Decision.REJECT:
            if not reason or not reason.strip():
                raise serializers.ValidationError(
                    {"reason": "A reason is required when rejecting a record."}
                )

        return attrs


class FinancialAuthorizationReadSerializer(serializers.ModelSerializer):
    """Read-only representation of an authorisation decision."""

    donation_id = serializers.UUIDField(read_only=True)
    fund_transaction_id = serializers.UUIDField(read_only=True)
    adjustment_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FinancialAuthorization
        fields = [
            "id",
            "donation_id",
            "fund_transaction_id",
            "adjustment_id",
            "decision",
            "decided_by",
            "decided_at",
            "reason",
            "correlation_id",
        ]
        read_only_fields = fields
