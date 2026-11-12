"""Restricted serializers for financial reporting responses."""

from rest_framework import serializers

from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FundTransaction,
)


class DonationReportSerializer(serializers.ModelSerializer):
    """Expose only fields required for financial reporting."""

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = Donation
        fields = [
            "id",
            "transaction_date",
            "amount",
            "currency_code",
            "category_id",
            "category_name",
            "payment_method",
            "status",
            "created_at",
            "authorised_at",
        ]
        read_only_fields = fields


class FundTransactionReportSerializer(serializers.ModelSerializer):
    """Expose fund transaction details without unnecessary free text."""

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = FundTransaction
        fields = [
            "id",
            "transaction_date",
            "amount",
            "currency_code",
            "category_id",
            "category_name",
            "transaction_type",
            "status",
            "created_at",
            "authorised_at",
        ]
        read_only_fields = fields


class FinancialAdjustmentReportSerializer(serializers.ModelSerializer):
    """Expose adjustment metadata without its free-text reason."""

    class Meta:
        model = FinancialAdjustment
        fields = [
            "id",
            "donation_id",
            "fund_transaction_id",
            "adjustment_type",
            "amount_delta",
            "status",
            "created_at",
        ]
        read_only_fields = fields
