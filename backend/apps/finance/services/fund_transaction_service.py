"""Business operations for fund transactions."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models.users import User
from apps.audit.services.audit_service import AuditService
from apps.finance.models import FundTransaction, FinancialCategory


class FundTransactionService:
    """Create and update fund transactions under financial access controls."""

    EDITABLE_FIELDS = {
        "transaction_date",
        "amount",
        "currency_code",
        "category",
        "transaction_type",
        "notes",
    }

    @staticmethod
    def _require_finance_actor(actor):
        """Require an active Pastor or Administrator."""

        if not isinstance(actor, User):
            raise ValidationError("A valid user is required.")

        if not actor.is_active:
            raise ValidationError("An inactive user cannot manage fund transactions.")

        has_permission = actor.role_assignments.filter(
            revoked_at__isnull=True,
            role__code__in=("PASTOR", "ADMINISTRATOR"),
        ).exists()

        if not has_permission:
            raise ValidationError(
                "Only an active Pastor or Administrator can manage fund transactions."
            )

    @staticmethod
    def _validate_uuid(value):
        """Accept a UUID or a valid UUID string."""

        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            raise ValidationError("A valid fund transaction ID is required.")

    @staticmethod
    def _snapshot(record):
        """Return a safe audit snapshot without free-text notes."""

        return {
            "id": str(record.id),
            "transaction_date": record.transaction_date.isoformat(),
            "amount": str(record.amount),
            "currency_code": record.currency_code,
            "category_id": str(record.category_id),
            "transaction_type": record.transaction_type,
            "status": record.status,
        }

    @staticmethod
    @transaction.atomic
    def create_transaction(
        *,
        actor,
        transaction_date,
        amount,
        currency_code,
        category,
        transaction_type,
        notes=None,
        correlation_id=None,
    ):
        """Create a pending fund transaction and its audit event."""

        FundTransactionService._require_finance_actor(actor)

        if not isinstance(category, FinancialCategory):
            raise ValidationError("A valid financial category is required.")

        record = FundTransaction(
            transaction_date=transaction_date,
            amount=amount,
            currency_code=currency_code,
            category=category,
            transaction_type=transaction_type,
            notes=notes,
            status=FundTransaction.Status.PENDING,
            created_by=actor,
            updated_by=actor,
        )

        record.full_clean()
        record.save()

        AuditService.record_event(
            actor=actor,
            entity_type="FundTransaction",
            entity_id=record.id,
            action="CREATE",
            after_data=FundTransactionService._snapshot(record),
            correlation_id=correlation_id,
        )

        return record

    @staticmethod
    @transaction.atomic
    def update_pending_transaction(
        *,
        actor,
        transaction_id,
        updates,
        correlation_id=None,
    ):
        """Update an editable pending transaction and audit the change."""

        FundTransactionService._require_finance_actor(actor)

        transaction_id = FundTransactionService._validate_uuid(transaction_id)

        if not isinstance(updates, dict) or not updates:
            raise ValidationError(
                "At least one fund transaction field must be supplied."
            )

        invalid_fields = set(updates) - FundTransactionService.EDITABLE_FIELDS

        if invalid_fields:
            raise ValidationError(
                {
                    "fields": (
                        "Unsupported or protected fields: "
                        + ", ".join(sorted(invalid_fields))
                    )
                }
            )

        try:
            record = (
                FundTransaction.objects.select_for_update()
                .select_related("category")
                .get(pk=transaction_id)
            )
        except FundTransaction.DoesNotExist:
            raise ValidationError("Fund transaction does not exist.")

        if record.status != FundTransaction.Status.PENDING:
            raise ValidationError("Only pending fund transactions can be edited.")

        before_data = FundTransactionService._snapshot(record)

        for field, value in updates.items():
            setattr(record, field, value)

        record.updated_by = actor
        record.updated_at = timezone.now()

        record.full_clean()
        record.save(
            update_fields=[
                *updates.keys(),
                "updated_by",
                "updated_at",
            ]
        )

        AuditService.record_event(
            actor=actor,
            entity_type="FundTransaction",
            entity_id=record.id,
            action="UPDATE",
            before_data=before_data,
            after_data=FundTransactionService._snapshot(record),
            correlation_id=correlation_id,
        )

        return record
