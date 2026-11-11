"""
Financial calculations for confirmed donations and fund transactions.

All calculations use Decimal values and preserve currency separation.
Only authorised transactions and authorised adjustments contribute
to confirmed financial totals.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FundTransaction,
)


ZERO = Decimal("0.00")


class FinancialCalculationService:
    """Calculate confirmed financial totals."""

    @staticmethod
    def _filter_dates(queryset, date_field, start_date=None, end_date=None):
        filters = {}

        if start_date is not None:
            filters[f"{date_field}__gte"] = start_date

        if end_date is not None:
            filters[f"{date_field}__lte"] = end_date

        if filters:
            queryset = queryset.filter(**filters)

        return queryset

    @staticmethod
    def _merge_totals(base_totals, adjustment_totals):
        result = dict(base_totals)

        for currency, amount in adjustment_totals.items():
            result[currency] = result.get(currency, ZERO) + amount

        return result

    @staticmethod
    def _donation_adjustment_totals(start_date=None, end_date=None):
        adjustments = FinancialAdjustment.objects.filter(
            status=FinancialAdjustment.Status.AUTHORISED,
            donation__status=Donation.Status.AUTHORISED,
        )

        adjustments = FinancialCalculationService._filter_dates(
            adjustments,
            "donation__transaction_date",
            start_date,
            end_date,
        )

        rows = adjustments.values("donation__currency_code").annotate(
            total=Sum("amount_delta")
        )

        return {row["donation__currency_code"]: row["total"] or ZERO for row in rows}

    @staticmethod
    def get_confirmed_donation_totals(start_date=None, end_date=None):
        """Return confirmed donation totals grouped by currency."""

        donations = Donation.objects.filter(
            status=Donation.Status.AUTHORISED,
        )

        donations = FinancialCalculationService._filter_dates(
            donations,
            "transaction_date",
            start_date,
            end_date,
        )

        rows = donations.values("currency_code").annotate(total=Sum("amount"))

        base_totals = {row["currency_code"]: row["total"] or ZERO for row in rows}

        adjustment_totals = FinancialCalculationService._donation_adjustment_totals(
            start_date,
            end_date,
        )

        return FinancialCalculationService._merge_totals(
            base_totals,
            adjustment_totals,
        )

    @staticmethod
    def _fund_adjustment_totals(start_date=None, end_date=None):
        adjustments = FinancialAdjustment.objects.filter(
            status=FinancialAdjustment.Status.AUTHORISED,
            fund_transaction__status=FundTransaction.Status.AUTHORISED,
        )

        adjustments = FinancialCalculationService._filter_dates(
            adjustments,
            "fund_transaction__transaction_date",
            start_date,
            end_date,
        )

        rows = adjustments.values(
            "fund_transaction__transaction_type",
            "fund_transaction__currency_code",
        ).annotate(total=Sum("amount_delta"))

        totals = {
            FundTransaction.TransactionType.INCOME: {},
            FundTransaction.TransactionType.EXPENSE: {},
        }

        for row in rows:
            transaction_type = row["fund_transaction__transaction_type"]
            currency = row["fund_transaction__currency_code"]

            totals[transaction_type][currency] = row["total"] or ZERO

        return totals

    @staticmethod
    def get_confirmed_fund_totals(start_date=None, end_date=None):
        """
        Return confirmed fund income and expense totals separately.

        The result is grouped by currency. No combined multi-currency
        balance is calculated.
        """

        transactions = FundTransaction.objects.filter(
            status=FundTransaction.Status.AUTHORISED,
        )

        transactions = FinancialCalculationService._filter_dates(
            transactions,
            "transaction_date",
            start_date,
            end_date,
        )

        rows = transactions.values(
            "transaction_type",
            "currency_code",
        ).annotate(total=Sum("amount"))

        base_totals = {
            FundTransaction.TransactionType.INCOME: {},
            FundTransaction.TransactionType.EXPENSE: {},
        }

        for row in rows:
            transaction_type = row["transaction_type"]
            currency = row["currency_code"]

            base_totals[transaction_type][currency] = row["total"] or ZERO

        adjustment_totals = FinancialCalculationService._fund_adjustment_totals(
            start_date,
            end_date,
        )

        return {
            FundTransaction.TransactionType.INCOME: FinancialCalculationService._merge_totals(
                base_totals[FundTransaction.TransactionType.INCOME],
                adjustment_totals[FundTransaction.TransactionType.INCOME],
            ),
            FundTransaction.TransactionType.EXPENSE: FinancialCalculationService._merge_totals(
                base_totals[FundTransaction.TransactionType.EXPENSE],
                adjustment_totals[FundTransaction.TransactionType.EXPENSE],
            ),
        }

    @classmethod
    def get_confirmed_financial_summary(cls, start_date=None, end_date=None):
        """Return confirmed donations, income, and expenses."""

        return {
            "donations": cls.get_confirmed_donation_totals(
                start_date,
                end_date,
            ),
            "fund_income": cls.get_confirmed_fund_totals(
                start_date,
                end_date,
            )[FundTransaction.TransactionType.INCOME],
            "fund_expenses": cls.get_confirmed_fund_totals(
                start_date,
                end_date,
            )[FundTransaction.TransactionType.EXPENSE],
        }
