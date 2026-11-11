"""Atomic authorisation workflow for financial records."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound

from apps.accounts.models.user_role import UserRole
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.finance.models.donation import Donation
from apps.finance.models.fund_transaction import FundTransaction
from apps.finance.models.financial_adjustment import FinancialAdjustment
from apps.finance.models.financial_authorization import FinancialAuthorization
from apps.finance.services.financial_adjustment_service import (
    FinancialAdjustmentService,
)


FINANCE_ROLE_CODES = ("PASTOR", "ADMINISTRATOR")


class FinancialAuthorizationConflict(APIException):
    status_code = 409
    default_detail = "This financial record has already been decided."
    default_code = "financial_authorization_conflict"


class FinancialAuthorizationService:

    @staticmethod
    def _require_finance_actor(actor):
        if (
            actor is None
            or not getattr(actor, "is_authenticated", False)
            or not getattr(actor, "is_active", False)
        ):
            raise ValidationError("An active Pastor or Administrator is required.")

        has_role = UserRole.objects.filter(
            user=actor,
            role__code__in=FINANCE_ROLE_CODES,
            revoked_at__isnull=True,
        ).exists()

        if not has_role:
            raise ValidationError("An active Pastor or Administrator is required.")

    @staticmethod
    def _validate_uuid(value, field_name):
        try:
            return UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            raise ValidationError({field_name: "A valid UUID is required."})

    @staticmethod
    def _snapshot(record, target_type):
        data = {
            "id": str(record.pk),
            "status": record.status,
        }

        if target_type == "donation":
            data.update(
                {
                    "transaction_date": record.transaction_date.isoformat(),
                    "amount": str(record.amount),
                    "currency_code": record.currency_code,
                    "category_id": str(record.category_id),
                    "is_anonymous": record.is_anonymous,
                }
            )

        elif target_type == "fund_transaction":
            data.update(
                {
                    "transaction_date": record.transaction_date.isoformat(),
                    "amount": str(record.amount),
                    "currency_code": record.currency_code,
                    "category_id": str(record.category_id),
                    "transaction_type": record.transaction_type,
                }
            )

        elif target_type == "adjustment":
            data.update(
                {
                    "donation_id": (
                        str(record.donation_id) if record.donation_id else None
                    ),
                    "fund_transaction_id": (
                        str(record.fund_transaction_id)
                        if record.fund_transaction_id
                        else None
                    ),
                    "adjustment_type": record.adjustment_type,
                    "amount_delta": str(record.amount_delta),
                    "reason": record.reason,
                }
            )

        return data

    @staticmethod
    @transaction.atomic
    def _decide(
        *,
        actor,
        target_type,
        target_id,
        decision,
        reason=None,
        correlation_id=None,
    ):
        FinancialAuthorizationService._require_finance_actor(actor)

        target_id = FinancialAuthorizationService._validate_uuid(
            target_id,
            "target_id",
        )

        if decision not in (
            FinancialAuthorization.Decision.AUTHORISE,
            FinancialAuthorization.Decision.REJECT,
        ):
            raise ValidationError({"decision": "Invalid decision."})

        if decision == FinancialAuthorization.Decision.REJECT:
            if not isinstance(reason, str) or not reason.strip():
                raise ValidationError(
                    {"reason": "A reason is required when rejecting a record."}
                )
            reason = reason.strip()
        elif reason is not None:
            if not isinstance(reason, str):
                raise ValidationError({"reason": "The reason must be a string."})
            reason = reason.strip() or None

        if correlation_id is not None:
            correlation_id = FinancialAuthorizationService._validate_uuid(
                correlation_id,
                "correlation_id",
            )

        targets = {
            "donation": (
                Donation,
                Donation.Status,
                "Donation",
            ),
            "fund_transaction": (
                FundTransaction,
                FundTransaction.Status,
                "FundTransaction",
            ),
            "adjustment": (
                FinancialAdjustment,
                FinancialAdjustment.Status,
                "FinancialAdjustment",
            ),
        }

        if target_type not in targets:
            raise ValidationError({"target_type": "Invalid financial target."})

        model, status_choices, entity_type = targets[target_type]

        try:
            record = model.objects.select_for_update().get(pk=target_id)
        except model.DoesNotExist:
            raise NotFound("The financial record was not found.")

        if record.status != status_choices.PENDING:
            raise FinancialAuthorizationConflict()

        if (
            target_type == "adjustment"
            and decision == FinancialAuthorization.Decision.AUTHORISE
        ):
            FinancialAdjustmentService.validate_for_authorisation(record)

        before_data = FinancialAuthorizationService._snapshot(
            record,
            target_type,
        )

        new_status = (
            status_choices.AUTHORISED
            if decision == FinancialAuthorization.Decision.AUTHORISE
            else status_choices.REJECTED
        )

        record.status = new_status

        update_fields = ["status", "updated_at"]

        if target_type == "adjustment":
            record.updated_by = actor
            update_fields.append("updated_by")
        else:
            record.updated_by = actor
            update_fields.append("updated_by")

        if decision == FinancialAuthorization.Decision.AUTHORISE and target_type in (
            "donation",
            "fund_transaction",
        ):
            record.authorised_by = actor
            record.authorised_at = timezone.now()
            update_fields.extend(["authorised_by", "authorised_at"])

        record.save(update_fields=update_fields)

        authorization = FinancialAuthorization.objects.create(
            **{
                target_type: record,
                "decision": decision,
                "decided_by": actor,
                "reason": reason,
                "correlation_id": correlation_id,
            }
        )

        after_data = FinancialAuthorizationService._snapshot(
            record,
            target_type,
        )

        AuditService.record_event(
            actor=actor,
            entity_type=entity_type,
            entity_id=record.pk,
            action=(
                AuditLog.Action.AUTHORISE
                if decision == FinancialAuthorization.Decision.AUTHORISE
                else AuditLog.Action.REJECT
            ),
            before_data=before_data,
            after_data=after_data,
            correlation_id=correlation_id,
        )

        return authorization

    @staticmethod
    def decide_donation(**kwargs):
        return FinancialAuthorizationService._decide(
            target_type="donation",
            **kwargs,
        )

    @staticmethod
    def decide_fund_transaction(**kwargs):
        return FinancialAuthorizationService._decide(
            target_type="fund_transaction",
            **kwargs,
        )

    @staticmethod
    def decide_adjustment(**kwargs):
        return FinancialAuthorizationService._decide(
            target_type="adjustment",
            **kwargs,
        )
