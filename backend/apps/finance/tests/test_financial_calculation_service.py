from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models.users import User
from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FinancialCategory,
    FundTransaction,
)
from apps.finance.services.financial_calculation_service import (
    FinancialCalculationService,
)


class FinancialCalculationServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.actor = User.objects.create_user(
            email="finance-calculation@example.com",
            password="test-password",
        )

        cls.category = FinancialCategory.objects.create(
            code="GENERAL",
            name="General",
            scope=FinancialCategory.Scope.BOTH,
            created_by=cls.actor,
        )

        cls.transaction_date = date(2026, 11, 10)

    def create_donation(self, amount, status, currency="MMK"):
        return Donation.objects.create(
            transaction_date=self.transaction_date,
            amount=Decimal(amount),
            currency_code=currency,
            category=self.category,
            payment_method="CASH",
            status=status,
            created_by=self.actor,
            updated_by=self.actor,
        )

    def create_fund_transaction(
        self,
        amount,
        transaction_type,
        status,
        currency="MMK",
    ):
        return FundTransaction.objects.create(
            transaction_date=self.transaction_date,
            amount=Decimal(amount),
            currency_code=currency,
            category=self.category,
            transaction_type=transaction_type,
            status=status,
            created_by=self.actor,
            updated_by=self.actor,
        )

    def create_adjustment(self, target, amount_delta, status):
        fields = {
            "amount_delta": Decimal(amount_delta),
            "adjustment_type": FinancialAdjustment.AdjustmentType.CORRECTION,
            "reason": "Calculation test adjustment",
            "status": status,
            "created_by": self.actor,
        }

        if isinstance(target, Donation):
            fields["donation"] = target
        else:
            fields["fund_transaction"] = target

        return FinancialAdjustment.objects.create(**fields)

    def test_donation_totals_include_only_authorised_records(self):
        self.create_donation(
            "100.00",
            Donation.Status.AUTHORISED,
        )

        self.create_donation(
            "200.00",
            Donation.Status.PENDING,
        )

        self.create_donation(
            "300.00",
            Donation.Status.REJECTED,
        )

        self.create_donation(
            "50.00",
            Donation.Status.AUTHORISED,
            currency="USD",
        )

        totals = FinancialCalculationService.get_confirmed_donation_totals()

        self.assertEqual(totals["MMK"], Decimal("100.00"))
        self.assertEqual(totals["USD"], Decimal("50.00"))

    def test_authorised_donation_adjustments_affect_confirmed_totals(self):
        donation = self.create_donation(
            "100.00",
            Donation.Status.AUTHORISED,
        )

        self.create_adjustment(
            donation,
            "25.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        self.create_adjustment(
            donation,
            "50.00",
            FinancialAdjustment.Status.PENDING,
        )

        totals = FinancialCalculationService.get_confirmed_donation_totals()

        self.assertEqual(totals["MMK"], Decimal("125.00"))

    def test_adjustments_for_pending_donations_are_excluded(self):
        donation = self.create_donation(
            "100.00",
            Donation.Status.PENDING,
        )

        self.create_adjustment(
            donation,
            "25.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        totals = FinancialCalculationService.get_confirmed_donation_totals()

        self.assertEqual(totals, {})

    def test_fund_income_and_expenses_are_separate(self):
        self.create_fund_transaction(
            "200.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            "80.00",
            FundTransaction.TransactionType.EXPENSE,
            FundTransaction.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            "500.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.PENDING,
        )

        totals = FinancialCalculationService.get_confirmed_fund_totals()

        self.assertEqual(
            totals[FundTransaction.TransactionType.INCOME]["MMK"],
            Decimal("200.00"),
        )

        self.assertEqual(
            totals[FundTransaction.TransactionType.EXPENSE]["MMK"],
            Decimal("80.00"),
        )

    def test_fund_adjustments_preserve_transaction_direction(self):
        income = self.create_fund_transaction(
            "200.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
        )

        expense = self.create_fund_transaction(
            "80.00",
            FundTransaction.TransactionType.EXPENSE,
            FundTransaction.Status.AUTHORISED,
        )

        self.create_adjustment(
            income,
            "10.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        self.create_adjustment(
            expense,
            "-20.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        totals = FinancialCalculationService.get_confirmed_fund_totals()

        self.assertEqual(
            totals[FundTransaction.TransactionType.INCOME]["MMK"],
            Decimal("210.00"),
        )

        self.assertEqual(
            totals[FundTransaction.TransactionType.EXPENSE]["MMK"],
            Decimal("60.00"),
        )

    def test_date_filters_use_original_transaction_date(self):
        old_donation = self.create_donation(
            "100.00",
            Donation.Status.AUTHORISED,
        )
        old_donation.transaction_date = date(2026, 10, 1)
        old_donation.save(update_fields=["transaction_date"])

        current_donation = self.create_donation(
            "200.00",
            Donation.Status.AUTHORISED,
        )

        totals = FinancialCalculationService.get_confirmed_donation_totals(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        self.assertEqual(totals["MMK"], Decimal("200.00"))
