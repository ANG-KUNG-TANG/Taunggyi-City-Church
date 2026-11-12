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
from apps.finance.selectors.donation_selectors import get_donations_for_report


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

        fund_totals = cls.get_confirmed_fund_totals(
            start_date,
            end_date,
        )

        return {
            "donations": cls.get_confirmed_donation_totals(
                start_date,
                end_date,
            ),
            "fund_income": fund_totals[FundTransaction.TransactionType.INCOME],
            "fund_expenses": fund_totals[FundTransaction.TransactionType.EXPENSE],
        }

    @staticmethod
    def get_daily_fund_report(report_date):
        """
        Return daily fund transactions grouped by category, type and currency.

        Pending and rejected transactions are reported separately.
        Only authorised transactions and authorised adjustments
        contribute to confirmed totals.
        """

        transactions = (
            FundTransaction.objects.filter(
                transaction_date=report_date,
            )
            .values(
                "category_id",
                "category__name",
                "transaction_type",
                "currency_code",
                "status",
            )
            .annotate(total=Sum("amount"))
        )

        groups = {}

        for row in transactions:
            key = (
                row["category_id"],
                row["transaction_type"],
                row["currency_code"],
            )

            if key not in groups:
                groups[key] = {
                    "category_id": row["category_id"],
                    "category_name": row["category__name"],
                    "transaction_type": row["transaction_type"],
                    "currency_code": row["currency_code"],
                    "authorised_total": ZERO,
                    "pending_total": ZERO,
                    "rejected_total": ZERO,
                    "authorised_adjustment_total": ZERO,
                    "confirmed_total": ZERO,
                }

            status_field = {
                FundTransaction.Status.AUTHORISED: "authorised_total",
                FundTransaction.Status.PENDING: "pending_total",
                FundTransaction.Status.REJECTED: "rejected_total",
            }[row["status"]]

            groups[key][status_field] += row["total"] or ZERO

        adjustments = (
            FinancialAdjustment.objects.filter(
                status=FinancialAdjustment.Status.AUTHORISED,
                fund_transaction__status=FundTransaction.Status.AUTHORISED,
                fund_transaction__transaction_date=report_date,
            )
            .values(
                "fund_transaction__category_id",
                "fund_transaction__category__name",
                "fund_transaction__transaction_type",
                "fund_transaction__currency_code",
            )
            .annotate(total=Sum("amount_delta"))
        )

        for row in adjustments:
            key = (
                row["fund_transaction__category_id"],
                row["fund_transaction__transaction_type"],
                row["fund_transaction__currency_code"],
            )

            if key not in groups:
                groups[key] = {
                    "category_id": row["fund_transaction__category_id"],
                    "category_name": row["fund_transaction__category__name"],
                    "transaction_type": row["fund_transaction__transaction_type"],
                    "currency_code": row["fund_transaction__currency_code"],
                    "authorised_total": ZERO,
                    "pending_total": ZERO,
                    "rejected_total": ZERO,
                    "authorised_adjustment_total": ZERO,
                    "confirmed_total": ZERO,
                }

            groups[key]["authorised_adjustment_total"] += row["total"] or ZERO

        for group in groups.values():
            group["confirmed_total"] = (
                group["authorised_total"] + group["authorised_adjustment_total"]
            )

        return sorted(
            groups.values(),
            key=lambda item: (
                item["category_name"],
                item["transaction_type"],
                item["currency_code"],
            ),
        )

    @staticmethod
    def get_daily_donation_report(report_date):
        """
        Return daily donations grouped by category, payment method and currency.

        Status totals are reported separately. Only authorised donations
        contribute to confirmed totals. Adjustments are excluded.
        """
        donations = get_donations_for_report(
            start_date=report_date,
            end_date=report_date,
        )

        groups = {}

        for donation in donations:
            key = (
                donation.category_id,
                donation.payment_method,
                donation.currency_code,
            )

            if key not in groups:
                groups[key] = {
                    "category_id": donation.category_id,
                    "category_name": donation.category.name,
                    "payment_method": donation.payment_method,
                    "currency_code": donation.currency_code,
                    "authorised_total": ZERO,
                    "pending_total": ZERO,
                    "rejected_total": ZERO,
                    "confirmed_total": ZERO,
                    "donations": [],
                }

            status_field = {
                Donation.Status.AUTHORISED: "authorised_total",
                Donation.Status.PENDING: "pending_total",
                Donation.Status.REJECTED: "rejected_total",
            }[donation.status]

            groups[key][status_field] += donation.amount

            if donation.status == Donation.Status.AUTHORISED:
                groups[key]["confirmed_total"] += donation.amount

            groups[key]["donations"].append(donation)

        return sorted(
            groups.values(),
            key=lambda item: (
                item["category_name"],
                item["payment_method"],
                item["currency_code"],
            ),
        )

    @staticmethod
    def get_monthly_donation_report(year, month):
        """
        Return monthly donation totals grouped by category and currency.

        Transaction statuses remain separate. Only authorised donations
        and authorised adjustments contribute to confirmed totals.
        """
        from calendar import monthrange

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])

        donations = (
            Donation.objects.filter(
                transaction_date__gte=start_date,
                transaction_date__lte=end_date,
            )
            .values(
                "category_id",
                "category__name",
                "currency_code",
                "status",
            )
            .annotate(total=Sum("amount"))
        )

        groups = {}

        for row in donations:
            key = (row["category_id"], row["currency_code"])

            if key not in groups:
                groups[key] = {
                    "category_id": row["category_id"],
                    "category_name": row["category__name"],
                    "currency_code": row["currency_code"],
                    "authorised_total": ZERO,
                    "pending_total": ZERO,
                    "rejected_total": ZERO,
                    "authorised_adjustment_total": ZERO,
                    "confirmed_total": ZERO,
                }

            status_field = {
                Donation.Status.AUTHORISED: "authorised_total",
                Donation.Status.PENDING: "pending_total",
                Donation.Status.REJECTED: "rejected_total",
            }[row["status"]]

            groups[key][status_field] += row["total"] or ZERO

        adjustments = (
            FinancialAdjustment.objects.filter(
                status=FinancialAdjustment.Status.AUTHORISED,
                donation__status=Donation.Status.AUTHORISED,
                donation__transaction_date__gte=start_date,
                donation__transaction_date__lte=end_date,
            )
            .values(
                "donation__category_id",
                "donation__category__name",
                "donation__currency_code",
            )
            .annotate(total=Sum("amount_delta"))
        )

        for row in adjustments:
            key = (
                row["donation__category_id"],
                row["donation__currency_code"],
            )

            if key not in groups:
                groups[key] = {
                    "category_id": row["donation__category_id"],
                    "category_name": row["donation__category__name"],
                    "currency_code": row["donation__currency_code"],
                    "authorised_total": ZERO,
                    "pending_total": ZERO,
                    "rejected_total": ZERO,
                    "authorised_adjustment_total": ZERO,
                    "confirmed_total": ZERO,
                }

            groups[key]["authorised_adjustment_total"] += row["total"] or ZERO

        for group in groups.values():
            group["confirmed_total"] = (
                group["authorised_total"] + group["authorised_adjustment_total"]
            )

        return sorted(
            groups.values(),
            key=lambda item: (
                item["category_name"],
                item["currency_code"],
            ),
        )

    @classmethod
    def get_monthly_income_report(cls, year, month):
        """
        Return monthly confirmed donation and fund income by currency.

        Only authorised transactions and authorised adjustments
        contribute to the reported totals. Fund expenses are excluded.
        """
        from calendar import monthrange

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])

        donation_totals = cls.get_confirmed_donation_totals(
            start_date=start_date,
            end_date=end_date,
        )

        fund_totals = cls.get_confirmed_fund_totals(
            start_date=start_date,
            end_date=end_date,
        )

        fund_income_totals = fund_totals[FundTransaction.TransactionType.INCOME]

        currencies = sorted(set(donation_totals) | set(fund_income_totals))

        results = []

        for currency in currencies:
            donation_income = donation_totals.get(currency, ZERO)
            fund_income = fund_income_totals.get(currency, ZERO)

            results.append(
                {
                    "currency_code": currency,
                    "donation_income": donation_income,
                    "fund_income": fund_income,
                    "total_income": donation_income + fund_income,
                }
            )

        return results
