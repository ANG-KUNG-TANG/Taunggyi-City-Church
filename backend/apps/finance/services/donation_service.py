"""Business operations for donation records."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models.users import User
from apps.audit.services.audit_service import AuditService
from apps.finance.models import Donation, FinancialCategory


class DonationService:
    """Create and update donations under financial access controls."""

    EDITABLE_FIELDS = {
        "transaction_date",
        "amount",
        "currency_code",
        "category",
        "payment_method",
        "donor_identity",
        "is_anonymous",
        "notes",
    }

    @staticmethod
    def _require_finance_actor(actor):
        """Require an active Pastor or Administrator."""

        if not isinstance(actor, User):
            raise ValidationError("A valid user is required.")

        if not actor.is_active:
            raise ValidationError("An inactive user cannot manage donations.")

        has_permission = actor.role_assignments.filter(
            revoked_at__isnull=True,
            role__code__in=("PASTOR", "ADMINISTRATOR"),
        ).exists()

        if not has_permission:
            raise ValidationError(
                "Only an active Pastor or Administrator can manage donations."
            )

    @staticmethod
    def _validate_uuid(value):
        """Accept a UUID or a valid UUID string."""

        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            raise ValidationError("A valid donation ID is required.")

    @staticmethod
    def _normalise_donor_identity(*, donor_identity, is_anonymous):
        """Never retain donor identity for an anonymous donation."""

        if is_anonymous:
            return None

        if donor_identity is None:
            return None

        if not isinstance(donor_identity, str):
            raise ValidationError("Donor identity must be text.")

        return donor_identity.strip() or None

    @staticmethod
    def _snapshot(donation):
        """Return a safe audit snapshot without personal free-text data."""

        return {
            "id": str(donation.id),
            "transaction_date": donation.transaction_date.isoformat(),
            "amount": str(donation.amount),
            "currency_code": donation.currency_code,
            "category_id": str(donation.category_id),
            "payment_method": donation.payment_method,
            "is_anonymous": donation.is_anonymous,
            "status": donation.status,
        }

    @staticmethod
    @transaction.atomic
    def create_donation(
        *,
        actor,
        transaction_date,
        amount,
        currency_code,
        category,
        payment_method,
        donor_identity=None,
        is_anonymous=False,
        notes=None,
        correlation_id=None,
    ):
        """Create a pending donation and its audit event."""

        DonationService._require_finance_actor(actor)

        if not isinstance(category, FinancialCategory):
            raise ValidationError("A valid financial category is required.")

        donor_identity = DonationService._normalise_donor_identity(
            donor_identity=donor_identity,
            is_anonymous=is_anonymous,
        )

        donation = Donation(
            transaction_date=transaction_date,
            amount=amount,
            currency_code=currency_code,
            category=category,
            payment_method=payment_method,
            donor_identity=donor_identity,
            is_anonymous=is_anonymous,
            notes=notes,
            status=Donation.Status.PENDING,
            created_by=actor,
            updated_by=actor,
        )

        donation.full_clean()
        donation.save()

        AuditService.record_event(
            actor=actor,
            entity_type="Donation",
            entity_id=donation.id,
            action="CREATE",
            after_data=DonationService._snapshot(donation),
            correlation_id=correlation_id,
        )

        return donation

    @staticmethod
    @transaction.atomic
    def update_pending_donation(
        *,
        actor,
        donation_id,
        updates,
        correlation_id=None,
    ):
        """Update an editable pending donation and record the change."""

        DonationService._require_finance_actor(actor)

        donation_id = DonationService._validate_uuid(donation_id)

        if not isinstance(updates, dict) or not updates:
            raise ValidationError("At least one donation field must be supplied.")

        invalid_fields = set(updates) - DonationService.EDITABLE_FIELDS

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
            donation = (
                Donation.objects.select_for_update()
                .select_related("category")
                .get(pk=donation_id)
            )
        except Donation.DoesNotExist:
            raise ValidationError("Donation does not exist.")

        if donation.status != Donation.Status.PENDING:
            raise ValidationError("Only pending donations can be edited.")

        before_data = DonationService._snapshot(donation)

        for field, value in updates.items():
            setattr(donation, field, value)

        donation.donor_identity = DonationService._normalise_donor_identity(
            donor_identity=donation.donor_identity,
            is_anonymous=donation.is_anonymous,
        )

        donation.updated_by = actor
        donation.updated_at = timezone.now()

        donation.full_clean()
        donation.save(
            update_fields=[
                *updates.keys(),
                "donor_identity",
                "updated_by",
                "updated_at",
            ]
        )

        AuditService.record_event(
            actor=actor,
            entity_type="Donation",
            entity_id=donation.id,
            action="UPDATE",
            before_data=before_data,
            after_data=DonationService._snapshot(donation),
            correlation_id=correlation_id,
        )

        return donation
