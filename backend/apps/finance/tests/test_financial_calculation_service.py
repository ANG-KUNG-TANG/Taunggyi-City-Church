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

    def test_confirmed_donation_totals_respect_date_range(self):
        old_donation = self.create_donation(
            "100.00",
            Donation.Status.AUTHORISED,
        )
        old_donation.transaction_date = date(2026, 10, 31)
        old_donation.save(update_fields=["transaction_date"])

        self.create_donation(
            "200.00",
            Donation.Status.AUTHORISED,
        )

        totals = FinancialCalculationService.get_confirmed_donation_totals(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        self.assertEqual(totals["MMK"], Decimal("200.00"))

    def test_pending_and_rejected_adjustments_do_not_affect_confirmed_totals(self):
        donation = self.create_donation(
            "100.00",
            Donation.Status.AUTHORISED,
        )

        self.create_adjustment(
            donation,
            "25.00",
            FinancialAdjustment.Status.PENDING,
        )

        self.create_adjustment(
            donation,
            "50.00",
            FinancialAdjustment.Status.REJECTED,
        )

        totals = FinancialCalculationService.get_confirmed_donation_totals()

        self.assertEqual(totals["MMK"], Decimal("100.00"))

    def test_fund_totals_preserve_currency_separation(self):
        self.create_fund_transaction(
            "200.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
            currency="MMK",
        )

        self.create_fund_transaction(
            "50.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
            currency="USD",
        )

        totals = FinancialCalculationService.get_confirmed_fund_totals()

        self.assertEqual(
            totals[FundTransaction.TransactionType.INCOME]["MMK"],
            Decimal("200.00"),
        )

        self.assertEqual(
            totals[FundTransaction.TransactionType.INCOME]["USD"],
            Decimal("50.00"),
        )

    def test_daily_fund_report_separates_statuses(self):
        self.create_fund_transaction(
            "200.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            "50.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.PENDING,
        )

        self.create_fund_transaction(
            "30.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.REJECTED,
        )

        report = FinancialCalculationService.get_daily_fund_report(
            report_date=self.transaction_date,
        )

        income = next(
            item
            for item in report
            if item["transaction_type"] == FundTransaction.TransactionType.INCOME
            and item["currency_code"] == "MMK"
        )

        self.assertEqual(income["authorised_total"], Decimal("200.00"))
        self.assertEqual(income["pending_total"], Decimal("50.00"))
        self.assertEqual(income["rejected_total"], Decimal("30.00"))
        self.assertEqual(income["authorised_adjustment_total"], Decimal("0.00"))
        self.assertEqual(income["confirmed_total"], Decimal("200.00"))

    def test_daily_fund_report_includes_authorised_adjustments(self):
        transaction = self.create_fund_transaction(
            "200.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
        )

        self.create_adjustment(
            transaction,
            "25.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        self.create_adjustment(
            transaction,
            "50.00",
            FinancialAdjustment.Status.PENDING,
        )

        report = FinancialCalculationService.get_daily_fund_report(
            report_date=self.transaction_date,
        )

        income = next(
            item
            for item in report
            if item["transaction_type"] == FundTransaction.TransactionType.INCOME
            and item["currency_code"] == "MMK"
        )

        self.assertEqual(income["authorised_total"], Decimal("200.00"))
        self.assertEqual(
            income["authorised_adjustment_total"],
            Decimal("25.00"),
        )
        self.assertEqual(income["confirmed_total"], Decimal("225.00"))

    def test_monthly_donation_report_separates_statuses(self):
        self.create_donation("200.00", Donation.Status.AUTHORISED)
        self.create_donation("50.00", Donation.Status.PENDING)
        self.create_donation("30.00", Donation.Status.REJECTED)

        report = FinancialCalculationService.get_monthly_donation_report(
            year=2026,
            month=11,
        )

        result = report[0]

        self.assertEqual(result["authorised_total"], Decimal("200.00"))
        self.assertEqual(result["pending_total"], Decimal("50.00"))
        self.assertEqual(result["rejected_total"], Decimal("30.00"))
        self.assertEqual(result["confirmed_total"], Decimal("200.00"))

    def test_monthly_donation_report_includes_authorised_adjustments(self):
        donation = self.create_donation("200.00", Donation.Status.AUTHORISED)

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

        report = FinancialCalculationService.get_monthly_donation_report(
            year=2026,
            month=11,
        )

        result = report[0]

        self.assertEqual(
            result["authorised_adjustment_total"],
            Decimal("25.00"),
        )
        self.assertEqual(result["confirmed_total"], Decimal("225.00"))

    def test_monthly_donation_report_preserves_currency_separation(self):
        self.create_donation(
            "200.00",
            Donation.Status.AUTHORISED,
            currency="MMK",
        )
        self.create_donation(
            "50.00",
            Donation.Status.AUTHORISED,
            currency="USD",
        )

        report = FinancialCalculationService.get_monthly_donation_report(
            year=2026,
            month=11,
        )

        totals = {item["currency_code"]: item["confirmed_total"] for item in report}

        self.assertEqual(totals["MMK"], Decimal("200.00"))
        self.assertEqual(totals["USD"], Decimal("50.00"))

    def test_monthly_donation_report_excludes_other_months(self):
        donation = self.create_donation("100.00", Donation.Status.AUTHORISED)
        donation.transaction_date = date(2026, 10, 31)
        donation.save(update_fields=["transaction_date"])

        self.create_donation("200.00", Donation.Status.AUTHORISED)

        report = FinancialCalculationService.get_monthly_donation_report(
            year=2026,
            month=11,
        )

        self.assertEqual(len(report), 1)
        self.assertEqual(
            report[0]["confirmed_total"],
            Decimal("200.00"),
        )

    def test_monthly_income_report_combines_confirmed_income_by_currency(self):
        donation = self.create_donation(
            "100.00",
            Donation.Status.AUTHORISED,
        )
        self.create_adjustment(
            donation,
            "10.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        self.create_donation(
            "20.00",
            Donation.Status.AUTHORISED,
            currency="USD",
        )

        self.create_donation(
            "500.00",
            Donation.Status.PENDING,
        )

        fund_income = self.create_fund_transaction(
            "50.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.AUTHORISED,
        )
        self.create_adjustment(
            fund_income,
            "5.00",
            FinancialAdjustment.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            "999.00",
            FundTransaction.TransactionType.EXPENSE,
            FundTransaction.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            "700.00",
            FundTransaction.TransactionType.INCOME,
            FundTransaction.Status.PENDING,
        )

        results = FinancialCalculationService.get_monthly_income_report(
            year=2026,
            month=11,
        )

        self.assertEqual(len(results), 2)

        by_currency = {item["currency_code"]: item for item in results}

        self.assertEqual(
            by_currency["MMK"]["donation_income"],
            Decimal("110.00"),
        )
        self.assertEqual(
            by_currency["MMK"]["fund_income"],
            Decimal("55.00"),
        )
        self.assertEqual(
            by_currency["MMK"]["total_income"],
            Decimal("165.00"),
        )

        self.assertEqual(
            by_currency["USD"]["donation_income"],
            Decimal("20.00"),
        )
        self.assertEqual(
            by_currency["USD"]["fund_income"],
            Decimal("0.00"),
        )
        self.assertEqual(
            by_currency["USD"]["total_income"],
            Decimal("20.00"),
        )
