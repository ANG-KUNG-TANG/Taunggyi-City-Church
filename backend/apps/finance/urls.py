"""URL configuration for finance APIs."""

from django.urls import path

from apps.finance.views.adjustment_views import (
    FinancialAdjustmentDetailView,
    FinancialAdjustmentListCreateView,
)
from apps.finance.views.authorizations_views import (
    DonationAuthorizationView,
    FinancialAdjustmentAuthorizationView,
    FundTransactionAuthorizationView,
)
from apps.finance.views.donation_views import (
    DonationDetailView,
    DonationListCreateView,
)
from apps.finance.views.financial_audit_views import (
    FinancialAuditHistoryView,
)
from apps.finance.views.financial_report_views import (
    FinancialSummaryReportView,
)
from apps.finance.views.fund_transaction_views import (
    FundTransactionDetailView,
    FundTransactionListCreateView,
)

urlpatterns = [
    path(
        "donations/",
        DonationListCreateView.as_view(),
        name="donation-list-create",
    ),
    path(
        "donations/<uuid:donation_id>/",
        DonationDetailView.as_view(),
        name="donation-detail",
    ),
    path(
        "donations/<uuid:target_id>/authorise/",
        DonationAuthorizationView.as_view(),
        name="donation-authorise",
    ),
    path(
        "fund-transactions/",
        FundTransactionListCreateView.as_view(),
        name="fund-transaction-list-create",
    ),
    path(
        "fund-transactions/<uuid:transaction_id>/",
        FundTransactionDetailView.as_view(),
        name="fund-transaction-detail",
    ),
    path(
        "fund-transactions/<uuid:target_id>/authorise/",
        FundTransactionAuthorizationView.as_view(),
        name="fund-transaction-authorise",
    ),
    path(
        "adjustments/",
        FinancialAdjustmentListCreateView.as_view(),
        name="financial-adjustment-list-create",
    ),
    path(
        "adjustments/<uuid:adjustment_id>/",
        FinancialAdjustmentDetailView.as_view(),
        name="financial-adjustment-detail",
    ),
    path(
        "adjustments/<uuid:target_id>/authorise/",
        FinancialAdjustmentAuthorizationView.as_view(),
        name="financial-adjustment-authorise",
    ),
    path(
        "audit-history/",
        FinancialAuditHistoryView.as_view(),
        name="financial-audit-history",
    ),
    path(
        "reports/summary/",
        FinancialSummaryReportView.as_view(),
        name="financial-summary-report",
    ),
]
