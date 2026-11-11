import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.finance.models.donation import currency_validator


class FundTransaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AUTHORISED = "AUTHORISED", "Authorised"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    transaction_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    currency_code = models.CharField(
        max_length=3,
        validators=[currency_validator],
    )

    category = models.ForeignKey(
        "tcc.FinancialCategory",
        on_delete=models.PROTECT,
        related_name="fund_transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )

    notes = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_fund_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_fund_transactions",
    )
    updated_at = models.DateTimeField(auto_now=True)

    authorised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authorised_fund_transactions",
        blank=True,
        null=True,
    )
    authorised_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "fund_transactions"
        ordering = ["-transaction_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["transaction_date", "status"],
                name="fund_date_status_idx",
            ),
            models.Index(
                fields=["category", "transaction_date"],
                name="fund_cat_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="fund_amount_positive_ck",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["PENDING", "AUTHORISED", "REJECTED"]),
                name="fund_status_valid_ck",
            ),
            models.CheckConstraint(
                condition=Q(transaction_type__in=["INCOME", "EXPENSE"]),
                name="fund_type_valid_ck",
            ),
        ]

    def clean(self):
        super().clean()

        if self.category_id:
            if not self.category.is_active:
                raise ValidationError(
                    {
                        "category": "Inactive categories cannot be used for new transactions."
                    }
                )

            if self.category.scope not in ("FUND", "BOTH"):
                raise ValidationError(
                    {"category": "Category must have FUND or BOTH scope."}
                )

    def __str__(self):
        return f"{self.transaction_type} " f"{self.amount} {self.currency_code}"
