import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class FinancialAdjustment(models.Model):
    class AdjustmentType(models.TextChoices):
        CORRECTION = "CORRECTION", "Correction"
        REVERSAL = "REVERSAL", "Reversal"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AUTHORISED = "AUTHORISED", "Authorised"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    donation = models.ForeignKey(
        "tcc.Donation",
        on_delete=models.PROTECT,
        related_name="adjustments",
        blank=True,
        null=True,
    )

    fund_transaction = models.ForeignKey(
        "tcc.FundTransaction",
        on_delete=models.PROTECT,
        related_name="adjustments",
        blank=True,
        null=True,
    )

    adjustment_type = models.CharField(
        max_length=20,
        choices=AdjustmentType.choices,
    )

    amount_delta = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_adjustments",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_financial_adjustments",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tcc"
        db_table = "financial_adjustments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["donation", "status"],
                name="adj_donation_status_idx",
            ),
            models.Index(
                fields=["fund_transaction", "status"],
                name="adj_fund_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        donation__isnull=False,
                        fund_transaction__isnull=True,
                    )
                    | Q(
                        donation__isnull=True,
                        fund_transaction__isnull=False,
                    )
                ),
                name="adjustment_one_target_ck",
            ),
            models.CheckConstraint(
                condition=~Q(amount_delta=0),
                name="adjustment_delta_nonzero_ck",
            ),
            models.CheckConstraint(
                condition=~Q(reason=""),
                name="adjustment_reason_required_ck",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["PENDING", "AUTHORISED", "REJECTED"]),
                name="adj_status_valid_ck",
            ),
            models.CheckConstraint(
                condition=Q(adjustment_type__in=["CORRECTION", "REVERSAL"]),
                name="adj_type_valid_ck",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.reason or not self.reason.strip():
            raise ValidationError({"reason": "An adjustment reason is required."})

        if len(self.reason.strip()) > 500:
            raise ValidationError(
                {"reason": "Adjustment reason cannot exceed 500 characters."}
            )

    def __str__(self):
        return f"{self.adjustment_type} - {self.amount_delta}"
