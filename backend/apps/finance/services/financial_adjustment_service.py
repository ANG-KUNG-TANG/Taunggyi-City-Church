"""Services for creating and updating pending financial adjustments."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum

from apps.accounts.models.user_role import UserRole
from apps.audit.services.audit_service import AuditService
from apps.finance.models.donation import Donation
from apps.finance.models.financial_adjustment import FinancialAdjustment
from apps.finance.models.fund_transaction import FundTransaction


ZERO = Decimal("0.00")
FINANCE_ROLE_CODES = ("PASTOR", "ADMINISTRATOR")


def _require_finance_actor(actor):
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or not getattr(actor, "is_active", False)
    ):
        raise ValidationError("An active Pastor or Administrator is required.")

    has_finance_role = UserRole.objects.filter(
        user=actor,
        role__code__in=FINANCE_ROLE_CODES,
        revoked_at__isnull=True,
    ).exists()

    if not has_finance_role:
        raise ValidationError("An active Pastor or Administrator is required.")


def _validate_uuid(value, field_name):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError({field_name: "A valid UUID is required."})


def _to_decimal(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"amount_delta": "Enter a valid decimal amount."})

    if not amount.is_finite():
        raise ValidationError({"amount_delta": "The amount must be finite."})

    return amount


def _lock_target(adjustment):
    if adjustment.donation_id is not None:
        target = Donation.objects.select_for_update().get(pk=adjustment.donation_id)
        if target.status != Donation.Status.AUTHORISED:
            raise ValidationError(
                "An adjustment can only target an authorised donation."
            )
        return target, "donation"

    if adjustment.fund_transaction_id is not None:
        target = FundTransaction.objects.select_for_update().get(
            pk=adjustment.fund_transaction_id
        )
        if target.status != FundTransaction.Status.AUTHORISED:
            raise ValidationError(
                "An adjustment can only target an authorised fund transaction."
            )
        return target, "fund_transaction"

    raise ValidationError("An adjustment must have exactly one target.")


def _target_adjustments_query(target, target_type):
    if target_type == "donation":
        return FinancialAdjustment.objects.filter(donation_id=target.pk)

    return FinancialAdjustment.objects.filter(fund_transaction_id=target.pk)


def _validate_reversal(
    *,
    adjustment,
    target,
    target_type,
    amount_delta,
    exclude_adjustment_id=None,
):
    """Validate sign and cumulative limit against the target's remaining amount."""

    adjustments = _target_adjustments_query(target, target_type)

    authorised_delta = (
        adjustments.filter(status=FinancialAdjustment.Status.AUTHORISED).aggregate(
            total=Sum("amount_delta")
        )["total"]
        or ZERO
    )

    pending_reversals = adjustments.filter(
        status=FinancialAdjustment.Status.PENDING,
        adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
    )

    if exclude_adjustment_id is not None:
        pending_reversals = pending_reversals.exclude(pk=exclude_adjustment_id)

    pending_reversal_delta = (
        pending_reversals.aggregate(total=Sum("amount_delta"))["total"] or ZERO
    )

    remaining_amount = target.amount + authorised_delta + pending_reversal_delta

    if remaining_amount == ZERO:
        raise ValidationError("No remaining authorised amount is available to reverse.")

    if remaining_amount > ZERO and amount_delta >= ZERO:
        raise ValidationError(
            "A reversal must be negative when the remaining amount is positive."
        )

    if remaining_amount < ZERO and amount_delta <= ZERO:
        raise ValidationError(
            "A reversal must be positive when the remaining amount is negative."
        )

    if abs(amount_delta) > abs(remaining_amount):
        raise ValidationError("The reversal exceeds the remaining authorised amount.")


def _snapshot(adjustment):
    return {
        "id": str(adjustment.pk),
        "donation_id": (
            str(adjustment.donation_id) if adjustment.donation_id else None
        ),
        "fund_transaction_id": (
            str(adjustment.fund_transaction_id)
            if adjustment.fund_transaction_id
            else None
        ),
        "adjustment_type": adjustment.adjustment_type,
        "amount_delta": str(adjustment.amount_delta),
        "reason": adjustment.reason,
        "status": adjustment.status,
    }


class FinancialAdjustmentService:
    @staticmethod
    @transaction.atomic
    def create_adjustment(
        *,
        actor,
        adjustment_type,
        amount_delta,
        reason,
        donation_id=None,
        fund_transaction_id=None,
        correlation_id=None,
    ):
        _require_finance_actor(actor)

        if (donation_id is None) == (fund_transaction_id is None):
            raise ValidationError("Specify exactly one donation or fund transaction.")

        amount_delta = _to_decimal(amount_delta)

        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError(
                {"reason": "A meaningful adjustment reason is required."}
            )

        reason = reason.strip()
        if len(reason) > 500:
            raise ValidationError(
                {"reason": "Adjustment reason cannot exceed 500 characters."}
            )

        adjustment = FinancialAdjustment(
            donation_id=(
                _validate_uuid(donation_id, "donation_id")
                if donation_id is not None
                else None
            ),
            fund_transaction_id=(
                _validate_uuid(fund_transaction_id, "fund_transaction_id")
                if fund_transaction_id is not None
                else None
            ),
            adjustment_type=adjustment_type,
            amount_delta=amount_delta,
            reason=reason.strip(),
            status=FinancialAdjustment.Status.PENDING,
            created_by=actor,
            updated_by=None,
        )

        target, target_type = _lock_target(adjustment)

        if adjustment.adjustment_type == FinancialAdjustment.AdjustmentType.REVERSAL:
            _validate_reversal(
                adjustment=adjustment,
                target=target,
                target_type=target_type,
                amount_delta=amount_delta,
            )

        adjustment.full_clean()
        adjustment.save()

        AuditService.record_event(
            actor=actor,
            entity_type="FinancialAdjustment",
            entity_id=adjustment.pk,
            action="CREATE",
            after_data=_snapshot(adjustment),
            correlation_id=correlation_id,
        )

        return adjustment

    @staticmethod
    @transaction.atomic
    def update_pending_adjustment(
        *,
        actor,
        adjustment_id,
        amount_delta=None,
        reason=None,
        correlation_id=None,
    ):
        _require_finance_actor(actor)
        adjustment_id = _validate_uuid(adjustment_id, "adjustment_id")

        adjustment = FinancialAdjustment.objects.select_for_update().get(
            pk=adjustment_id
        )

        if adjustment.status != FinancialAdjustment.Status.PENDING:
            raise ValidationError("Only pending adjustments can be updated.")

        before_data = _snapshot(adjustment)
        target, target_type = _lock_target(adjustment)

        if amount_delta is not None:
            adjustment.amount_delta = _to_decimal(amount_delta)

        if reason is not None:
            if not isinstance(reason, str) or not reason.strip():
                raise ValidationError(
                    {"reason": "A meaningful adjustment reason is required."}
                )

            reason = reason.strip()
            if len(reason) > 500:
                raise ValidationError(
                    {"reason": "Adjustment reason cannot exceed 500 characters."}
                )

            adjustment.reason = reason

        if adjustment.adjustment_type == FinancialAdjustment.AdjustmentType.REVERSAL:
            _validate_reversal(
                adjustment=adjustment,
                target=target,
                target_type=target_type,
                amount_delta=adjustment.amount_delta,
                exclude_adjustment_id=adjustment.pk,
            )

        adjustment.updated_by = actor
        adjustment.full_clean()
        adjustment.save(
            update_fields=[
                "amount_delta",
                "reason",
                "updated_by",
                "updated_at",
            ]
        )

        AuditService.record_event(
            actor=actor,
            entity_type="FinancialAdjustment",
            entity_id=adjustment.pk,
            action="UPDATE",
            before_data=before_data,
            after_data=_snapshot(adjustment),
            correlation_id=correlation_id,
        )

        return adjustment

    @staticmethod
    def validate_for_authorisation(adjustment):
        """
        Revalidate a pending reversal inside the caller's atomic approval
        transaction, after the target record has been locked.
        """
        if adjustment.status != FinancialAdjustment.Status.PENDING:
            raise ValidationError("Only pending adjustments can be authorised.")

        target, target_type = _lock_target(adjustment)

        if adjustment.adjustment_type == FinancialAdjustment.AdjustmentType.REVERSAL:
            _validate_reversal(
                adjustment=adjustment,
                target=target,
                target_type=target_type,
                amount_delta=adjustment.amount_delta,
                exclude_adjustment_id=adjustment.pk,
            )

        return adjustment
