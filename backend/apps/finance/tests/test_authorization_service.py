from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.exceptions import NotFound

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FinancialAuthorization,
    FinancialCategory,
    FundTransaction,
)
from apps.finance.services.authorization_service import (
    FinancialAuthorizationConflict,
    FinancialAuthorizationService,
)
from apps.finance.services.donation_service import DonationService
from apps.finance.services.fund_transaction_service import (
    FundTransactionService,
)
from apps.finance.services.financial_adjustment_service import (
    FinancialAdjustmentService,
)


class FinancialAuthorizationServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pastor = User.objects.create_user(
            email="pastor-authorization@example.com",
            password="test-password",
        )

        UserRole.objects.create(
            user=cls.pastor,
            role=Role.objects.get(code="PASTOR"),
        )

        cls.unauthorised_user = User.objects.create_user(
            email="unauthorised-authorization@example.com",
            password="test-password",
        )

        cls.donation_category = FinancialCategory.objects.create(
            code="AUTH_DONATION",
            name="Authorisation Donations",
            scope=FinancialCategory.Scope.DONATION,
            created_by=cls.pastor,
        )

        cls.fund_category = FinancialCategory.objects.create(
            code="AUTH_FUND",
            name="Authorisation Fund",
            scope=FinancialCategory.Scope.FUND,
            created_by=cls.pastor,
        )

    def create_pending_donation(self, **overrides):
        data = {
            "actor": self.pastor,
            "transaction_date": date(2026, 11, 11),
            "amount": Decimal("100.00"),
            "currency_code": "MMK",
            "category": self.donation_category,
            "payment_method": "CASH",
        }
        data.update(overrides)
        return DonationService.create_donation(**data)

    def create_pending_fund_transaction(self, **overrides):
        data = {
            "actor": self.pastor,
            "transaction_date": date(2026, 11, 11),
            "amount": Decimal("100.00"),
            "currency_code": "MMK",
            "category": self.fund_category,
            "transaction_type": FundTransaction.TransactionType.INCOME,
        }
        data.update(overrides)
        return FundTransactionService.create_transaction(**data)

    def create_authorised_donation(self):
        return Donation.objects.create(
            transaction_date=date(2026, 11, 11),
            amount=Decimal("100.00"),
            currency_code="MMK",
            category=self.donation_category,
            payment_method="CASH",
            status=Donation.Status.AUTHORISED,
            created_by=self.pastor,
            updated_by=self.pastor,
            authorised_by=self.pastor,
        )

    def test_authorises_pending_donation(self):
        donation = self.create_pending_donation()

        event = FinancialAuthorizationService.decide_donation(
            actor=self.pastor,
            target_id=donation.id,
            decision=FinancialAuthorization.Decision.AUTHORISE,
        )

        donation.refresh_from_db()

        self.assertEqual(event.decision, FinancialAuthorization.Decision.AUTHORISE)
        self.assertEqual(event.donation_id, donation.id)
        self.assertEqual(event.decided_by, self.pastor)
        self.assertEqual(donation.status, Donation.Status.AUTHORISED)
        self.assertEqual(donation.authorised_by, self.pastor)
        self.assertIsNotNone(donation.authorised_at)

        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="Donation",
                entity_id=donation.id,
                action=AuditLog.Action.AUTHORISE,
            ).exists()
        )

    def test_rejects_pending_fund_transaction_with_reason(self):
        record = self.create_pending_fund_transaction()

        event = FinancialAuthorizationService.decide_fund_transaction(
            actor=self.pastor,
            target_id=record.id,
            decision=FinancialAuthorization.Decision.REJECT,
            reason="Supporting documentation is insufficient.",
        )

        record.refresh_from_db()

        self.assertEqual(record.status, FundTransaction.Status.REJECTED)
        self.assertEqual(
            event.reason,
            "Supporting documentation is insufficient.",
        )
        self.assertEqual(event.fund_transaction_id, record.id)

        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="FundTransaction",
                entity_id=record.id,
                action=AuditLog.Action.REJECT,
            ).exists()
        )

    def test_rejection_requires_a_reason(self):
        donation = self.create_pending_donation()

        with self.assertRaises(ValidationError):
            FinancialAuthorizationService.decide_donation(
                actor=self.pastor,
                target_id=donation.id,
                decision=FinancialAuthorization.Decision.REJECT,
                reason="   ",
            )

        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertFalse(
            FinancialAuthorization.objects.filter(
                donation=donation,
            ).exists()
        )

    def test_authorisation_reason_must_be_a_string(self):
        donation = self.create_pending_donation()

        with self.assertRaises(ValidationError):
            FinancialAuthorizationService.decide_donation(
                actor=self.pastor,
                target_id=donation.id,
                decision=FinancialAuthorization.Decision.AUTHORISE,
                reason=123,
            )

        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.PENDING)

    def test_second_decision_returns_conflict(self):
        donation = self.create_pending_donation()

        FinancialAuthorizationService.decide_donation(
            actor=self.pastor,
            target_id=donation.id,
            decision=FinancialAuthorization.Decision.AUTHORISE,
        )

        with self.assertRaises(FinancialAuthorizationConflict):
            FinancialAuthorizationService.decide_donation(
                actor=self.pastor,
                target_id=donation.id,
                decision=FinancialAuthorization.Decision.REJECT,
                reason="Attempted second decision.",
            )

        self.assertEqual(
            FinancialAuthorization.objects.filter(
                donation=donation,
            ).count(),
            1,
        )

    def test_unauthorised_user_cannot_decide(self):
        donation = self.create_pending_donation()

        with self.assertRaises(ValidationError):
            FinancialAuthorizationService.decide_donation(
                actor=self.unauthorised_user,
                target_id=donation.id,
                decision=FinancialAuthorization.Decision.AUTHORISE,
            )

        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertFalse(
            FinancialAuthorization.objects.filter(
                donation=donation,
            ).exists()
        )

    def test_missing_target_returns_not_found(self):
        with self.assertRaises(NotFound):
            FinancialAuthorizationService.decide_donation(
                actor=self.pastor,
                target_id=uuid4(),
                decision=FinancialAuthorization.Decision.AUTHORISE,
            )

    def test_authorises_valid_adjustment(self):
        donation = self.create_authorised_donation()

        adjustment = FinancialAdjustmentService.create_adjustment(
            actor=self.pastor,
            donation_id=donation.id,
            adjustment_type=FinancialAdjustment.AdjustmentType.CORRECTION,
            amount_delta=Decimal("-10.00"),
            reason="Correcting the original recorded amount.",
        )

        event = FinancialAuthorizationService.decide_adjustment(
            actor=self.pastor,
            target_id=adjustment.id,
            decision=FinancialAuthorization.Decision.AUTHORISE,
        )

        adjustment.refresh_from_db()

        self.assertEqual(
            adjustment.status,
            FinancialAdjustment.Status.AUTHORISED,
        )
        self.assertEqual(event.adjustment_id, adjustment.id)
        self.assertEqual(adjustment.updated_by, self.pastor)

    def test_audit_failure_rolls_back_decision(self):
        donation = self.create_pending_donation()

        with patch(
            "apps.finance.services.authorization_service.AuditService.record_event",
            side_effect=RuntimeError("Audit storage unavailable."),
        ):
            with self.assertRaises(RuntimeError):
                FinancialAuthorizationService.decide_donation(
                    actor=self.pastor,
                    target_id=donation.id,
                    decision=FinancialAuthorization.Decision.AUTHORISE,
                )

        donation.refresh_from_db()

        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertIsNone(donation.authorised_by)
        self.assertIsNone(donation.authorised_at)
        self.assertFalse(
            FinancialAuthorization.objects.filter(
                donation=donation,
            ).exists()
        )

    def test_anonymous_donor_identity_is_not_in_authorisation_audit(self):
        donation = self.create_pending_donation(
            donor_identity="Private Donor",
            is_anonymous=True,
        )

        FinancialAuthorizationService.decide_donation(
            actor=self.pastor,
            target_id=donation.id,
            decision=FinancialAuthorization.Decision.AUTHORISE,
        )

        event = AuditLog.objects.get(
            entity_type="Donation",
            entity_id=donation.id,
            action=AuditLog.Action.AUTHORISE,
        )

        self.assertNotIn("donor_identity", event.before_data)
        self.assertNotIn("donor_identity", event.after_data)
        self.assertNotIn("Private Donor", str(event.before_data))
        self.assertNotIn("Private Donor", str(event.after_data))
