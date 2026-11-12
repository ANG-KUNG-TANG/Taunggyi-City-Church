from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FinancialCategory,
    FundTransaction,
)
from apps.finance.services.financial_adjustment_service import (
    FinancialAdjustmentService,
)


class FinancialAdjustmentServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pastor = User.objects.create_user(
            email="pastor-adjustment@example.com",
            password="test-password",
        )

        UserRole.objects.create(
            user=cls.pastor,
            role=Role.objects.get(code="PASTOR"),
        )

        cls.unauthorised_user = User.objects.create_user(
            email="unauthorised-adjustment@example.com",
            password="test-password",
        )

        cls.donation_category = FinancialCategory.objects.create(
            code="ADJ_DONATION",
            name="Adjustment Donations",
            scope=FinancialCategory.Scope.DONATION,
            created_by=cls.pastor,
        )

        cls.fund_category = FinancialCategory.objects.create(
            code="ADJ_FUND",
            name="Adjustment Fund",
            scope=FinancialCategory.Scope.FUND,
            created_by=cls.pastor,
        )

    def create_authorised_donation(self, amount="100.00"):
        return Donation.objects.create(
            transaction_date=date(2026, 11, 11),
            amount=Decimal(amount),
            currency_code="MMK",
            category=self.donation_category,
            payment_method="CASH",
            status=Donation.Status.AUTHORISED,
            created_by=self.pastor,
            updated_by=self.pastor,
            authorised_by=self.pastor,
        )

    def create_authorised_fund_transaction(self, amount="100.00"):
        return FundTransaction.objects.create(
            transaction_date=date(2026, 11, 11),
            amount=Decimal(amount),
            currency_code="MMK",
            category=self.fund_category,
            transaction_type=FundTransaction.TransactionType.EXPENSE,
            status=FundTransaction.Status.AUTHORISED,
            created_by=self.pastor,
            updated_by=self.pastor,
            authorised_by=self.pastor,
        )

    def create_adjustment(self, **overrides):
        donation = self.create_authorised_donation()

        data = {
            "actor": self.pastor,
            "donation_id": donation.id,
            "adjustment_type": FinancialAdjustment.AdjustmentType.CORRECTION,
            "amount_delta": Decimal("-10.00"),
            "reason": "Correcting the recorded donation amount.",
        }
        data.update(overrides)

        return FinancialAdjustmentService.create_adjustment(**data)

    def test_create_correction_starts_as_pending(self):
        adjustment = self.create_adjustment()

        self.assertEqual(
            adjustment.status,
            FinancialAdjustment.Status.PENDING,
        )
        self.assertEqual(adjustment.created_by, self.pastor)
        self.assertIsNone(adjustment.updated_by)

    def test_create_adjustment_for_fund_transaction(self):
        transaction = self.create_authorised_fund_transaction()

        adjustment = FinancialAdjustmentService.create_adjustment(
            actor=self.pastor,
            fund_transaction_id=transaction.id,
            adjustment_type=FinancialAdjustment.AdjustmentType.CORRECTION,
            amount_delta=Decimal("-15.00"),
            reason="Correcting the recorded fund expense.",
        )

        self.assertEqual(
            adjustment.fund_transaction_id,
            transaction.id,
        )
        self.assertIsNone(adjustment.donation_id)
        self.assertEqual(
            adjustment.status,
            FinancialAdjustment.Status.PENDING,
        )

    def test_create_reversal_with_valid_negative_amount(self):
        donation = self.create_authorised_donation()

        adjustment = FinancialAdjustmentService.create_adjustment(
            actor=self.pastor,
            donation_id=donation.id,
            adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
            amount_delta=Decimal("-40.00"),
            reason="Reversing an incorrectly recorded donation.",
        )

        self.assertEqual(
            adjustment.adjustment_type,
            FinancialAdjustment.AdjustmentType.REVERSAL,
        )
        self.assertEqual(adjustment.amount_delta, Decimal("-40.00"))

    def test_create_requires_finance_role(self):
        donation = self.create_authorised_donation()

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.create_adjustment(
                actor=self.unauthorised_user,
                donation_id=donation.id,
                adjustment_type=FinancialAdjustment.AdjustmentType.CORRECTION,
                amount_delta=Decimal("-10.00"),
                reason="A valid correction reason.",
            )

        self.assertEqual(FinancialAdjustment.objects.count(), 0)

    def test_exactly_one_target_is_required(self):
        donation = self.create_authorised_donation()
        fund_transaction = self.create_authorised_fund_transaction()

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.create_adjustment(
                actor=self.pastor,
                donation_id=donation.id,
                fund_transaction_id=fund_transaction.id,
                adjustment_type=FinancialAdjustment.AdjustmentType.CORRECTION,
                amount_delta=Decimal("-10.00"),
                reason="An adjustment with two targets.",
            )

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.create_adjustment(
                actor=self.pastor,
                adjustment_type=FinancialAdjustment.AdjustmentType.CORRECTION,
                amount_delta=Decimal("-10.00"),
                reason="An adjustment without a target.",
            )

    def test_pending_source_transaction_cannot_be_adjusted(self):
        donation = Donation.objects.create(
            transaction_date=date(2026, 11, 11),
            amount=Decimal("100.00"),
            currency_code="MMK",
            category=self.donation_category,
            payment_method="CASH",
            status=Donation.Status.PENDING,
            created_by=self.pastor,
            updated_by=self.pastor,
        )

        with self.assertRaises(ValidationError):
            self.create_adjustment(donation_id=donation.id)

        self.assertEqual(FinancialAdjustment.objects.count(), 0)

    def test_adjustment_reason_is_required(self):
        donation = self.create_authorised_donation()

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.create_adjustment(
                actor=self.pastor,
                donation_id=donation.id,
                adjustment_type=FinancialAdjustment.AdjustmentType.CORRECTION,
                amount_delta=Decimal("-10.00"),
                reason="   ",
            )

    def test_zero_adjustment_amount_is_rejected(self):
        donation = self.create_authorised_donation()

        with self.assertRaises(ValidationError):
            self.create_adjustment(
                donation_id=donation.id,
                amount_delta=Decimal("0.00"),
            )

    def test_reversal_must_have_opposite_sign(self):
        donation = self.create_authorised_donation()

        with self.assertRaises(ValidationError):
            self.create_adjustment(
                donation_id=donation.id,
                adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
                amount_delta=Decimal("20.00"),
            )

    def test_reversal_cannot_exceed_original_amount(self):
        donation = self.create_authorised_donation()

        with self.assertRaises(ValidationError):
            self.create_adjustment(
                donation_id=donation.id,
                adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
                amount_delta=Decimal("-100.01"),
            )

    def test_reversal_accepts_exact_remaining_amount(self):
        donation = self.create_authorised_donation()

        adjustment = self.create_adjustment(
            donation_id=donation.id,
            adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
            amount_delta=Decimal("-100.00"),
        )

        self.assertEqual(adjustment.amount_delta, Decimal("-100.00"))
        self.assertEqual(
            adjustment.status,
            FinancialAdjustment.Status.PENDING,
        )

    def test_pending_reversals_cannot_exceed_remaining_amount(self):
        donation = self.create_authorised_donation()

        self.create_adjustment(
            donation_id=donation.id,
            adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
            amount_delta=Decimal("-60.00"),
        )

        with self.assertRaises(ValidationError):
            self.create_adjustment(
                donation_id=donation.id,
                adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
                amount_delta=Decimal("-50.00"),
            )

        self.assertEqual(FinancialAdjustment.objects.count(), 1)

    def test_pending_adjustment_can_be_updated(self):
        adjustment = self.create_adjustment()

        updated = FinancialAdjustmentService.update_pending_adjustment(
            actor=self.pastor,
            adjustment_id=adjustment.id,
            amount_delta=Decimal("-20.00"),
            reason="Updated correction reason.",
        )

        self.assertEqual(updated.amount_delta, Decimal("-20.00"))
        self.assertEqual(updated.reason, "Updated correction reason.")
        self.assertEqual(updated.updated_by, self.pastor)

        event = AuditLog.objects.filter(
            entity_type="FinancialAdjustment",
            entity_id=adjustment.id,
            action=AuditLog.Action.UPDATE,
        ).latest("occurred_at")

        self.assertEqual(event.before_data["amount_delta"], "-10.00")
        self.assertEqual(event.after_data["amount_delta"], "-20.00")

    def test_update_revalidates_reversal_limit(self):
        adjustment = self.create_adjustment(
            adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
            amount_delta=Decimal("-60.00"),
        )

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.update_pending_adjustment(
                actor=self.pastor,
                adjustment_id=adjustment.id,
                amount_delta=Decimal("-101.00"),
            )

        adjustment.refresh_from_db()
        self.assertEqual(adjustment.amount_delta, Decimal("-60.00"))

    def test_authorised_adjustment_cannot_be_updated(self):
        adjustment = self.create_adjustment()
        adjustment.status = FinancialAdjustment.Status.AUTHORISED
        adjustment.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.update_pending_adjustment(
                actor=self.pastor,
                adjustment_id=adjustment.id,
                amount_delta=Decimal("-20.00"),
            )

    def test_create_records_audit_event(self):
        adjustment = self.create_adjustment()

        event = AuditLog.objects.get(
            entity_type="FinancialAdjustment",
            entity_id=adjustment.id,
        )

        self.assertEqual(event.action, AuditLog.Action.CREATE)
        self.assertEqual(
            event.after_data["amount_delta"],
            "-10.00",
        )
        self.assertNotIn("donor_identity", event.after_data)

    def test_authorisation_validation_accepts_pending_correction(self):
        adjustment = self.create_adjustment()

        validated = FinancialAdjustmentService.validate_for_authorisation(adjustment)

        self.assertEqual(validated, adjustment)

    def test_authorisation_validation_rechecks_reversal_limit(self):
        donation = self.create_authorised_donation()

        adjustment = FinancialAdjustment.objects.create(
            donation=donation,
            adjustment_type=FinancialAdjustment.AdjustmentType.REVERSAL,
            amount_delta=Decimal("-101.00"),
            reason="A reversal that exceeds the remaining amount.",
            status=FinancialAdjustment.Status.PENDING,
            created_by=self.pastor,
        )

        with self.assertRaises(ValidationError):
            FinancialAdjustmentService.validate_for_authorisation(adjustment)
