"""Serializers for financial adjustment requests and responses."""

from rest_framework import serializers

from apps.finance.models.financial_adjustment import FinancialAdjustment


class FinancialAdjustmentReadSerializer(serializers.ModelSerializer):
    """Read-only representation of a financial adjustment."""

    donation_id = serializers.UUIDField(read_only=True)
    fund_transaction_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FinancialAdjustment
        fields = [
            "id",
            "donation_id",
            "fund_transaction_id",
            "adjustment_type",
            "amount_delta",
            "reason",
            "status",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        ]
        read_only_fields = fields


class FinancialAdjustmentCreateSerializer(serializers.Serializer):
    """Validate data required to create a financial adjustment."""

    donation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    fund_transaction_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    adjustment_type = serializers.ChoiceField(
        choices=FinancialAdjustment.AdjustmentType.choices,
    )
    amount_delta = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    reason = serializers.CharField()

    def validate_amount_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Adjustment amount cannot be zero.")
        return value

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("An adjustment reason is required.")
        return value

    def validate(self, attrs):
        has_donation = attrs.get("donation_id") is not None
        has_fund_transaction = attrs.get("fund_transaction_id") is not None

        if has_donation == has_fund_transaction:
            raise serializers.ValidationError(
                "Provide exactly one of donation_id or " "fund_transaction_id."
            )

        return attrs


class FinancialAdjustmentUpdateSerializer(serializers.Serializer):
    """Validate fields editable on a pending financial adjustment."""

    amount_delta = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
    )
    reason = serializers.CharField(required=False)

    def validate_amount_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Adjustment amount cannot be zero.")
        return value

    def validate_reason(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("An adjustment reason is required.")
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one adjustment field must be provided."
            )
        return attrs
