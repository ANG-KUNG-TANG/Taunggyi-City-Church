from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.finance.models import Donation, FinancialCategory
from apps.finance.services.donation_service import DonationService


class DonationServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pastor = User.objects.create_user(
            email="pastor-finance@example.com",
            password="test-password",
        )

        pastor_role = Role.objects.get(code="PASTOR")

        UserRole.objects.create(
            user=cls.pastor,
            role=pastor_role,
        )

        cls.unauthorised_user = User.objects.create_user(
            email="unauthorised-finance@example.com",
            password="test-password",
        )

        cls.category = FinancialCategory.objects.create(
            code="DONATION_GENERAL",
            name="General Donations",
            scope=FinancialCategory.Scope.DONATION,
            created_by=cls.pastor,
        )

    def create_donation(self, **overrides):
        data = {
            "actor": self.pastor,
            "transaction_date": date(2026, 11, 11),
            "amount": Decimal("100.00"),
            "currency_code": "MMK",
            "category": self.category,
            "payment_method": "CASH",
        }
        data.update(overrides)
        return DonationService.create_donation(**data)

    def test_create_donation_starts_as_pending(self):
        donation = self.create_donation()

        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertEqual(donation.created_by, self.pastor)
        self.assertEqual(donation.updated_by, self.pastor)

    def test_anonymous_donation_does_not_store_identity(self):
        donation = self.create_donation(
            donor_identity="Private Donor",
            is_anonymous=True,
        )

        self.assertTrue(donation.is_anonymous)
        self.assertIsNone(donation.donor_identity)

    def test_create_requires_pastor_or_administrator(self):
        with self.assertRaises(ValidationError):
            self.create_donation(actor=self.unauthorised_user)

        self.assertEqual(Donation.objects.count(), 0)

    def test_create_records_audit_without_donor_identity_or_notes(self):
        donation = self.create_donation(
            donor_identity="Named Donor",
            notes="Private donor information",
        )

        event = AuditLog.objects.get(
            entity_type="Donation",
            entity_id=donation.id,
        )

        self.assertEqual(event.action, AuditLog.Action.CREATE)
        self.assertNotIn("donor_identity", event.after_data)
        self.assertNotIn("notes", event.after_data)

    def test_pending_donation_can_be_updated(self):
        donation = self.create_donation()

        updated = DonationService.update_pending_donation(
            actor=self.pastor,
            donation_id=donation.id,
            updates={"amount": Decimal("150.00")},
        )

        self.assertEqual(updated.amount, Decimal("150.00"))
        self.assertEqual(updated.updated_by, self.pastor)

        event = AuditLog.objects.filter(
            entity_type="Donation",
            entity_id=donation.id,
            action=AuditLog.Action.UPDATE,
        ).latest("occurred_at")

        self.assertEqual(event.before_data["amount"], "100.00")
        self.assertEqual(event.after_data["amount"], "150.00")

    def test_anonymous_update_clears_existing_identity(self):
        donation = self.create_donation(
            donor_identity="Named Donor",
        )

        updated = DonationService.update_pending_donation(
            actor=self.pastor,
            donation_id=donation.id,
            updates={
                "is_anonymous": True,
            },
        )

        self.assertIsNone(updated.donor_identity)

    def test_authorised_donation_cannot_be_updated(self):
        donation = self.create_donation()
        donation.status = Donation.Status.AUTHORISED
        donation.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            DonationService.update_pending_donation(
                actor=self.pastor,
                donation_id=donation.id,
                updates={"amount": Decimal("200.00")},
            )

    def test_status_cannot_be_changed_through_update_service(self):
        donation = self.create_donation()

        with self.assertRaises(ValidationError):
            DonationService.update_pending_donation(
                actor=self.pastor,
                donation_id=donation.id,
                updates={"status": Donation.Status.AUTHORISED},
            )

    def test_invalid_category_scope_is_rejected(self):
        fund_category = FinancialCategory.objects.create(
            code="FUND_ONLY",
            name="Fund Only",
            scope=FinancialCategory.Scope.FUND,
            created_by=self.pastor,
        )

        with self.assertRaises(ValidationError):
            self.create_donation(category=fund_category)
