"""Serializers for fund transaction requests and responses."""

from rest_framework import serializers

from apps.finance.models.fund_transaction import FundTransaction
from decimal import Decimal


class FundTransactionReadSerializer(serializers.ModelSerializer):
    """Read-only representation of a fund transaction."""

    category_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FundTransaction
        fields = [
            "id",
            "transaction_date",
            "amount",
            "currency_code",
            "category_id",
            "transaction_type",
            "notes",
            "status",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "authorised_by",
            "authorised_at",
        ]
        read_only_fields = fields


class FundTransactionCreateSerializer(serializers.Serializer):
    """Validate data required to create a fund transaction."""

    transaction_date = serializers.DateField()
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    currency_code = serializers.RegexField(
        regex=r"^[A-Z]{3}$",
        max_length=3,
    )
    category_id = serializers.UUIDField()
    transaction_type = serializers.ChoiceField(
        choices=FundTransaction.TransactionType.choices,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class FundTransactionUpdateSerializer(serializers.Serializer):
    """Validate fields editable on a pending fund transaction."""

    transaction_date = serializers.DateField(required=False)
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    currency_code = serializers.RegexField(
        regex=r"^[A-Z]{3}$",
        max_length=3,
        required=False,
    )
    category_id = serializers.UUIDField(required=False)
    transaction_type = serializers.ChoiceField(
        choices=FundTransaction.TransactionType.choices,
        required=False,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one fund transaction field must be provided."
            )
        return attrs
