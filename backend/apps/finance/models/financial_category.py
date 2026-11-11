import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class FinancialCategory(models.Model):
    class Scope(models.TextChoices):
        DONATION = "DONATION", "Donation"
        FUND = "FUND", "Fund"
        BOTH = "BOTH", "Both"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_categories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tcc"
        db_table = "financial_categories"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(scope__in=["DONATION", "FUND", "BOTH"]),
                name="fin_cat_scope_valid_ck",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
