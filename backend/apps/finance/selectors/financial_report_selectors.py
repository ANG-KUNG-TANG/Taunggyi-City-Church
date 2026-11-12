"""Database selectors for consolidated financial reports."""

from django.db.models import Q

from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FundTransaction,
)

from apps.finance.selectors.donation_selectors import (
    get_donations_for_report,
)

from apps.finance.selectors.fund_selectors import (
    get_fund_transactions_for_report,
)


def get_adjustments_for_report(
    start_date=None,
    end_date=None,
    category_id=None,
    currency_code=None,
    status=None,
):
    """Return adjustments filtered through their original transactions."""

    queryset = FinancialAdjustment.objects.select_related(
        "donation",
        "donation__category",
        "fund_transaction",
        "fund_transaction__category",
        "created_by",
        "updated_by",
    )

    if start_date is not None:
        queryset = queryset.filter(
            Q(donation__transaction_date__gte=start_date)
            | Q(fund_transaction__transaction_date__gte=start_date)
        )

    if end_date is not None:
        queryset = queryset.filter(
            Q(donation__transaction_date__lte=end_date)
            | Q(fund_transaction__transaction_date__lte=end_date)
        )

    if category_id is not None:
        queryset = queryset.filter(
            Q(donation__category_id=category_id)
            | Q(fund_transaction__category_id=category_id)
        )

    if currency_code is not None:
        queryset = queryset.filter(
            Q(donation__currency_code=currency_code)
            | Q(fund_transaction__currency_code=currency_code)
        )

    if status is not None:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


def get_pending_financial_records(
    start_date=None,
    end_date=None,
):
    """Return pending donations, fund transactions and adjustments."""

    return {
        "donations": get_donations_for_report(
            start_date=start_date,
            end_date=end_date,
            status=Donation.Status.PENDING,
        ),
        "fund_transactions": get_fund_transactions_for_report(
            start_date=start_date,
            end_date=end_date,
            status=FundTransaction.Status.PENDING,
        ),
        "adjustments": get_adjustments_for_report(
            start_date=start_date,
            end_date=end_date,
            status=FinancialAdjustment.Status.PENDING,
        ),
    }


def get_authorised_financial_records(
    start_date=None,
    end_date=None,
):
    """Return authorised source transactions and authorised adjustments."""

    adjustments = get_adjustments_for_report(
        start_date=start_date,
        end_date=end_date,
        status=FinancialAdjustment.Status.AUTHORISED,
    ).filter(
        Q(
            donation__isnull=False,
            donation__status=Donation.Status.AUTHORISED,
        )
        | Q(
            fund_transaction__isnull=False,
            fund_transaction__status=FundTransaction.Status.AUTHORISED,
        )
    )

    return {
        "donations": get_donations_for_report(
            start_date=start_date,
            end_date=end_date,
            status=Donation.Status.AUTHORISED,
        ),
        "fund_transactions": get_fund_transactions_for_report(
            start_date=start_date,
            end_date=end_date,
            status=FundTransaction.Status.AUTHORISED,
        ),
        "adjustments": adjustments,
    }
