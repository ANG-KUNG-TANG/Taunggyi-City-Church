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
from apps.finance.selectors.donation_selectors import (
    get_donations_for_report,
)
from apps.finance.selectors.fund_selectors import (
    get_fund_transactions_for_report,
)
from apps.finance.selectors.financial_report_selectors import (
    get_adjustments_for_report,
    get_pending_financial_records,
    get_authorised_financial_records,
)


class FinancialReportSelectorTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.actor = User.objects.create_user(
            email="report-selector@example.com",
            password="test-password",
        )

        cls.donation_category = FinancialCategory.objects.create(
            code="REPORT_DONATION",
            name="Report Donations",
            scope=FinancialCategory.Scope.DONATION,
            created_by=cls.actor,
        )

        cls.fund_category = FinancialCategory.objects.create(
            code="REPORT_FUND",
            name="Report Fund",
            scope=FinancialCategory.Scope.FUND,
            created_by=cls.actor,
        )

        cls.transaction_date = date(2026, 11, 15)

    def create_donation(
        self,
        amount="100.00",
        status=Donation.Status.PENDING,
        category=None,
        transaction_date=None,
        currency="MMK",
    ):
        return Donation.objects.create(
            transaction_date=transaction_date or self.transaction_date,
            amount=Decimal(amount),
            currency_code=currency,
            category=category or self.donation_category,
            payment_method="CASH",
            donor_identity="Private donor",
            status=status,
            created_by=self.actor,
            updated_by=self.actor,
        )

    def create_fund_transaction(
        self,
        amount="100.00",
        status=FundTransaction.Status.PENDING,
        category=None,
        transaction_date=None,
        currency="MMK",
        transaction_type=FundTransaction.TransactionType.INCOME,
    ):
        return FundTransaction.objects.create(
            transaction_date=transaction_date or self.transaction_date,
            amount=Decimal(amount),
            currency_code=currency,
            category=category or self.fund_category,
            transaction_type=transaction_type,
            status=status,
            created_by=self.actor,
            updated_by=self.actor,
        )

    def create_adjustment(
        self,
        target,
        status=FinancialAdjustment.Status.PENDING,
        amount_delta="-10.00",
    ):
        fields = {
            "amount_delta": Decimal(amount_delta),
            "adjustment_type": FinancialAdjustment.AdjustmentType.CORRECTION,
            "reason": "Financial report selector test.",
            "status": status,
            "created_by": self.actor,
        }

        if isinstance(target, Donation):
            fields["donation"] = target
        else:
            fields["fund_transaction"] = target

        return FinancialAdjustment.objects.create(**fields)

    def test_donation_selector_applies_inclusive_date_filters(self):
        first = self.create_donation(
            transaction_date=date(2026, 11, 1),
        )
        middle = self.create_donation(
            transaction_date=date(2026, 11, 15),
        )
        last = self.create_donation(
            transaction_date=date(2026, 11, 30),
        )
        self.create_donation(
            transaction_date=date(2026, 10, 31),
        )
        self.create_donation(
            transaction_date=date(2026, 12, 1),
        )

        results = get_donations_for_report(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        self.assertSetEqual(
            set(results.values_list("id", flat=True)),
            {first.id, middle.id, last.id},
        )

    def test_donation_selector_filters_category_currency_and_status(self):
        matching = self.create_donation(
            category=self.donation_category,
            currency="MMK",
            status=Donation.Status.AUTHORISED,
        )

        self.create_donation(
            category=self.donation_category,
            currency="USD",
            status=Donation.Status.AUTHORISED,
        )

        self.create_donation(
            category=self.donation_category,
            currency="MMK",
            status=Donation.Status.PENDING,
        )

        results = get_donations_for_report(
            category_id=self.donation_category.id,
            currency_code="MMK",
            status=Donation.Status.AUTHORISED,
        )

        self.assertEqual(
            list(results.values_list("id", flat=True)),
            [matching.id],
        )

    def test_donation_selector_defers_private_fields(self):
        donation = self.create_donation()

        result = get_donations_for_report().get(id=donation.id)

        self.assertIn("donor_identity", result.get_deferred_fields())
        self.assertIn("notes", result.get_deferred_fields())

    def test_fund_selector_filters_transaction_type_and_status(self):
        matching = self.create_fund_transaction(
            transaction_type=FundTransaction.TransactionType.EXPENSE,
            status=FundTransaction.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            transaction_type=FundTransaction.TransactionType.INCOME,
            status=FundTransaction.Status.AUTHORISED,
        )

        self.create_fund_transaction(
            transaction_type=FundTransaction.TransactionType.EXPENSE,
            status=FundTransaction.Status.PENDING,
        )

        results = get_fund_transactions_for_report(
            transaction_type=FundTransaction.TransactionType.EXPENSE,
            status=FundTransaction.Status.AUTHORISED,
        )

        self.assertEqual(
            list(results.values_list("id", flat=True)),
            [matching.id],
        )

    def test_adjustment_selector_uses_original_transaction_filters(self):
        matching_donation = self.create_donation(
            transaction_date=date(2026, 11, 15),
            currency="MMK",
        )
        matching_adjustment = self.create_adjustment(matching_donation)

        outside_date = self.create_donation(
            transaction_date=date(2026, 10, 31),
            currency="MMK",
        )
        self.create_adjustment(outside_date)

        other_currency = self.create_donation(
            transaction_date=date(2026, 11, 15),
            currency="USD",
        )
        self.create_adjustment(other_currency)

        results = get_adjustments_for_report(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            category_id=self.donation_category.id,
            currency_code="MMK",
        )

        self.assertEqual(
            list(results.values_list("id", flat=True)),
            [matching_adjustment.id],
        )

    def test_adjustment_selector_filters_fund_transaction_targets(self):
        transaction = self.create_fund_transaction(
            transaction_date=date(2026, 11, 15),
            currency="MMK",
        )
        adjustment = self.create_adjustment(transaction)

        results = get_adjustments_for_report(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            category_id=self.fund_category.id,
            currency_code="MMK",
        )

        self.assertEqual(
            list(results.values_list("id", flat=True)),
            [adjustment.id],
        )

    def test_pending_report_separates_pending_record_types(self):
        pending_donation = self.create_donation(
            status=Donation.Status.PENDING,
        )
        pending_fund = self.create_fund_transaction(
            status=FundTransaction.Status.PENDING,
        )
        pending_adjustment = self.create_adjustment(
            pending_donation,
            status=FinancialAdjustment.Status.PENDING,
        )

        self.create_donation(status=Donation.Status.AUTHORISED)
        self.create_fund_transaction(status=FundTransaction.Status.REJECTED)
        self.create_adjustment(
            pending_fund,
            status=FinancialAdjustment.Status.REJECTED,
        )

        results = get_pending_financial_records(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        self.assertSetEqual(
            set(results["donations"].values_list("id", flat=True)),
            {pending_donation.id},
        )
        self.assertSetEqual(
            set(results["fund_transactions"].values_list("id", flat=True)),
            {pending_fund.id},
        )
        self.assertSetEqual(
            set(results["adjustments"].values_list("id", flat=True)),
            {pending_adjustment.id},
        )

    def test_authorised_report_excludes_pending_and_rejected_records(self):
        authorised_donation = self.create_donation(
            status=Donation.Status.AUTHORISED,
        )
        authorised_fund = self.create_fund_transaction(
            status=FundTransaction.Status.AUTHORISED,
        )
        authorised_adjustment = self.create_adjustment(
            authorised_donation,
            status=FinancialAdjustment.Status.AUTHORISED,
        )

        self.create_donation(status=Donation.Status.PENDING)
        self.create_fund_transaction(status=FundTransaction.Status.REJECTED)
        self.create_adjustment(
            authorised_fund,
            status=FinancialAdjustment.Status.PENDING,
        )

        results = get_authorised_financial_records(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        self.assertSetEqual(
            set(results["donations"].values_list("id", flat=True)),
            {authorised_donation.id},
        )
        self.assertSetEqual(
            set(results["fund_transactions"].values_list("id", flat=True)),
            {authorised_fund.id},
        )
        self.assertSetEqual(
            set(results["adjustments"].values_list("id", flat=True)),
            {authorised_adjustment.id},
        )

    def test_authorised_report_excludes_adjustments_with_unauthorised_sources(self):
        pending_donation = self.create_donation(
            status=Donation.Status.PENDING,
        )
        rejected_donation = self.create_donation(
            status=Donation.Status.REJECTED,
        )
        pending_fund = self.create_fund_transaction(
            status=FundTransaction.Status.PENDING,
        )
        rejected_fund = self.create_fund_transaction(
            status=FundTransaction.Status.REJECTED,
        )

        pending_donation_adjustment = self.create_adjustment(
            pending_donation,
            status=FinancialAdjustment.Status.AUTHORISED,
        )
        rejected_donation_adjustment = self.create_adjustment(
            rejected_donation,
            status=FinancialAdjustment.Status.AUTHORISED,
        )
        pending_fund_adjustment = self.create_adjustment(
            pending_fund,
            status=FinancialAdjustment.Status.AUTHORISED,
        )
        rejected_fund_adjustment = self.create_adjustment(
            rejected_fund,
            status=FinancialAdjustment.Status.AUTHORISED,
        )

        results = get_authorised_financial_records(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        self.assertFalse(
            results["adjustments"]
            .filter(
                id__in=[
                    pending_donation_adjustment.id,
                    rejected_donation_adjustment.id,
                    pending_fund_adjustment.id,
                    rejected_fund_adjustment.id,
                ]
            )
            .exists()
        )
