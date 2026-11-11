import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class FinancialAuthorizationQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Financial authorization decisions cannot be updated.")

    def delete(self):
        raise ValidationError("Financial authorization decisions cannot be deleted.")


class FinancialAuthorization(models.Model):
    class Decision(models.TextChoices):
        AUTHORISE = "AUTHORISE", "Authorise"
        REJECT = "REJECT", "Reject"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    donation = models.ForeignKey(
        "tcc.Donation",
        on_delete=models.PROTECT,
        related_name="authorization_events",
        blank=True,
        null=True,
    )

    fund_transaction = models.ForeignKey(
        "tcc.FundTransaction",
        on_delete=models.PROTECT,
        related_name="authorization_events",
        blank=True,
        null=True,
    )

    adjustment = models.ForeignKey(
        "tcc.FinancialAdjustment",
        on_delete=models.PROTECT,
        related_name="authorization_events",
        blank=True,
        null=True,
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financial_decisions",
    )

    decided_at = models.DateTimeField(auto_now_add=True)

    reason = models.TextField(
        blank=True,
        null=True,
    )

    correlation_id = models.UUIDField(
        blank=True,
        null=True,
    )

    objects = FinancialAuthorizationQuerySet.as_manager()

    class Meta:
        app_label = "tcc"
        db_table = "financial_authorizations"
        ordering = ["-decided_at"]
        indexes = [
            models.Index(
                fields=["donation", "decided_at"],
                name="auth_donation_date_idx",
            ),
            models.Index(
                fields=["fund_transaction", "decided_at"],
                name="auth_fund_date_idx",
            ),
            models.Index(
                fields=["adjustment", "decided_at"],
                name="auth_adjustment_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        donation__isnull=False,
                        fund_transaction__isnull=True,
                        adjustment__isnull=True,
                    )
                    | Q(
                        donation__isnull=True,
                        fund_transaction__isnull=False,
                        adjustment__isnull=True,
                    )
                    | Q(
                        donation__isnull=True,
                        fund_transaction__isnull=True,
                        adjustment__isnull=False,
                    )
                ),
                name="auth_exactly_one_target_ck",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(decision="REJECT") | (Q(reason__isnull=False) & ~Q(reason=""))
                ),
                name="auth_reject_reason_ck",
            ),
            models.CheckConstraint(
                condition=Q(decision__in=["AUTHORISE", "REJECT"]),
                name="auth_decision_valid_ck",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Financial authorization decisions are immutable.")

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Financial authorization decisions cannot be deleted.")

    def __str__(self):
        return f"{self.decision} - {self.id}"
