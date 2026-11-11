import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


currency_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Currency code must contain exactly three uppercase letters.",
)


class Donation(models.Model):
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
        related_name="donations",
    )

    payment_method = models.CharField(max_length=40)
    donor_identity = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )
    is_anonymous = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_donations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_donations",
    )
    updated_at = models.DateTimeField(auto_now=True)

    authorised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authorised_donations",
        blank=True,
        null=True,
    )
    authorised_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "donations"
        ordering = ["-transaction_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["transaction_date", "status"],
                name="don_date_status_idx",
            ),
            models.Index(
                fields=["category", "transaction_date"],
                name="don_cat_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="don_amount_positive_ck",
            ),
            models.CheckConstraint(
                condition=(Q(is_anonymous=False) | Q(donor_identity__isnull=True)),
                name="don_anonymous_identity_ck",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["PENDING", "AUTHORISED", "REJECTED"]),
                name="don_status_valid_ck",
            ),
        ]

    def clean(self):
        super().clean()

        if self.category_id:
            if not self.category.is_active:
                raise ValidationError(
                    {
                        "category": "Inactive categories cannot be used for new donations."
                    }
                )

            if self.category.scope not in (
                "DONATION",
                "BOTH",
            ):
                raise ValidationError(
                    {"category": "Category must have DONATION or BOTH scope."}
                )

        if self.is_anonymous and self.donor_identity:
            raise ValidationError(
                {"donor_identity": "Anonymous donations cannot store donor identity."}
            )

    def __str__(self):
        return f"Donation {self.id} - {self.amount} {self.currency_code}"
