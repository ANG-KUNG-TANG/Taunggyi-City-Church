"""Database selectors for financial donation reports."""

from apps.finance.models import Donation


def get_donations_for_report(
    start_date=None,
    end_date=None,
    category_id=None,
    currency_code=None,
    status=None,
):
    """Return donations matching the supplied report filters."""

    queryset = Donation.objects.select_related(
        "category",
        "created_by",
        "updated_by",
        "authorised_by",
    ).defer(
        "donor_identity",
        "notes",
    )

    if start_date is not None:
        queryset = queryset.filter(transaction_date__gte=start_date)

    if end_date is not None:
        queryset = queryset.filter(transaction_date__lte=end_date)

    if category_id is not None:
        queryset = queryset.filter(category_id=category_id)

    if currency_code is not None:
        queryset = queryset.filter(currency_code=currency_code)

    if status is not None:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-transaction_date", "-created_at")
