"""Serializers for donation requests and responses."""

from rest_framework import serializers

from apps.finance.models.donation import Donation
from decimal import Decimal


class DonationReadSerializer(serializers.ModelSerializer):
    """Read-only representation of a donation."""

    category_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Donation
        fields = [
            "id",
            "transaction_date",
            "amount",
            "currency_code",
            "category_id",
            "payment_method",
            "donor_identity",
            "is_anonymous",
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


class DonationCreateSerializer(serializers.Serializer):
    """Validate data required to create a donation."""

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
    payment_method = serializers.CharField(max_length=40)
    donor_identity = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    is_anonymous = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_payment_method(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Payment method is required.")
        return value


class DonationUpdateSerializer(serializers.Serializer):
    """Validate fields editable on a pending donation."""

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
    payment_method = serializers.CharField(
        max_length=40,
        required=False,
    )
    donor_identity = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    is_anonymous = serializers.BooleanField(required=False)
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_payment_method(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Payment method is required.")
        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one donation field must be provided."
            )
        return attrs
