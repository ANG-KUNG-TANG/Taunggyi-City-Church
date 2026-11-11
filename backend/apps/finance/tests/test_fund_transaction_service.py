from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.finance.models import FundTransaction, FinancialCategory
from apps.finance.services.fund_transaction_service import (
    FundTransactionService,
)


class FundTransactionServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pastor = User.objects.create_user(
            email="pastor-fund@example.com",
            password="test-password",
        )

        UserRole.objects.create(
            user=cls.pastor,
            role=Role.objects.get(code="PASTOR"),
        )

        cls.unauthorised_user = User.objects.create_user(
            email="unauthorised-fund@example.com",
            password="test-password",
        )

        cls.category = FinancialCategory.objects.create(
            code="FUND_GENERAL",
            name="General Fund",
            scope=FinancialCategory.Scope.FUND,
            created_by=cls.pastor,
        )

    def create_transaction(self, **overrides):
        data = {
            "actor": self.pastor,
            "transaction_date": date(2026, 11, 11),
            "amount": Decimal("100.00"),
            "currency_code": "MMK",
            "category": self.category,
            "transaction_type": FundTransaction.TransactionType.INCOME,
        }
        data.update(overrides)
        return FundTransactionService.create_transaction(**data)

    def test_create_transaction_starts_as_pending(self):
        record = self.create_transaction()

        self.assertEqual(record.status, FundTransaction.Status.PENDING)
        self.assertEqual(record.created_by, self.pastor)
        self.assertEqual(record.updated_by, self.pastor)

    def test_create_expense_transaction(self):
        record = self.create_transaction(
            transaction_type=FundTransaction.TransactionType.EXPENSE,
        )

        self.assertEqual(
            record.transaction_type,
            FundTransaction.TransactionType.EXPENSE,
        )

    def test_create_requires_pastor_or_administrator(self):
        with self.assertRaises(ValidationError):
            self.create_transaction(actor=self.unauthorised_user)

        self.assertEqual(FundTransaction.objects.count(), 0)

    def test_create_records_audit_without_notes(self):
        record = self.create_transaction(notes="Private transaction notes")

        event = AuditLog.objects.get(
            entity_type="FundTransaction",
            entity_id=record.id,
        )

        self.assertEqual(event.action, AuditLog.Action.CREATE)
        self.assertNotIn("notes", event.after_data)

    def test_pending_transaction_can_be_updated(self):
        record = self.create_transaction()

        updated = FundTransactionService.update_pending_transaction(
            actor=self.pastor,
            transaction_id=record.id,
            updates={"amount": Decimal("150.00")},
        )

        self.assertEqual(updated.amount, Decimal("150.00"))
        self.assertEqual(updated.updated_by, self.pastor)

        event = AuditLog.objects.filter(
            entity_type="FundTransaction",
            entity_id=record.id,
            action=AuditLog.Action.UPDATE,
        ).latest("occurred_at")

        self.assertEqual(event.before_data["amount"], "100.00")
        self.assertEqual(event.after_data["amount"], "150.00")

    def test_authorised_transaction_cannot_be_updated(self):
        record = self.create_transaction()
        record.status = FundTransaction.Status.AUTHORISED
        record.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            FundTransactionService.update_pending_transaction(
                actor=self.pastor,
                transaction_id=record.id,
                updates={"amount": Decimal("200.00")},
            )

    def test_status_cannot_be_changed_through_update_service(self):
        record = self.create_transaction()

        with self.assertRaises(ValidationError):
            FundTransactionService.update_pending_transaction(
                actor=self.pastor,
                transaction_id=record.id,
                updates={"status": FundTransaction.Status.AUTHORISED},
            )

    def test_invalid_category_scope_is_rejected(self):
        donation_category = FinancialCategory.objects.create(
            code="DONATION_ONLY",
            name="Donation Only",
            scope=FinancialCategory.Scope.DONATION,
            created_by=self.pastor,
        )

        with self.assertRaises(ValidationError):
            self.create_transaction(category=donation_category)

    def test_invalid_transaction_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.create_transaction(transaction_type="TRANSFER")
