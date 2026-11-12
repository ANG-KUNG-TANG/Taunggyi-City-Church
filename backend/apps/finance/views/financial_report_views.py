"""Protected financial reporting API views."""

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.services.financial_calculation_service import (
    FinancialCalculationService,
)
from apps.finance.selectors.financial_report_selectors import (
    get_pending_financial_records,
)
from apps.finance.serializers.financial_report_serializers import (
    DonationReportSerializer,
    FinancialAdjustmentReportSerializer,
    FundTransactionReportSerializer,
)


class FinancialSummaryQuerySerializer(serializers.Serializer):
    """Validate optional financial report date filters."""

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "End date must not precede start date."}
            )

        return attrs


class FinancialSummaryReportView(APIView):
    """Return authorised financial totals grouped by currency."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        query_serializer = FinancialSummaryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        filters = query_serializer.validated_data

        summary = FinancialCalculationService.get_confirmed_financial_summary(
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
        )

        return Response(
            {
                "start_date": filters.get("start_date"),
                "end_date": filters.get("end_date"),
                "confirmed": summary,
            }
        )


class DailyFundReportQuerySerializer(serializers.Serializer):
    """Validate the date required for a daily fund report."""

    date = serializers.DateField(required=True)


class DailyFundReportView(APIView):
    """Return daily fund totals grouped by category, type and currency."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        query_serializer = DailyFundReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        report_date = query_serializer.validated_data["date"]

        results = FinancialCalculationService.get_daily_fund_report(
            report_date=report_date
        )

        return Response(
            {
                "date": report_date,
                "results": results,
            }
        )


class DailyDonationReportView(APIView):
    """Return daily donation details and totals."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        query_serializer = DailyDonationReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        report_date = query_serializer.validated_data["date"]

        results = FinancialCalculationService.get_daily_donation_report(
            report_date=report_date
        )

        for group in results:
            group["donations"] = DonationReportSerializer(
                group["donations"],
                many=True,
            ).data

        return Response(
            {
                "date": report_date,
                "results": results,
            }
        )


class MonthlyDonationReportQuerySerializer(serializers.Serializer):
    """Validate the year and month required for a monthly donation report."""

    year = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=9999,
    )
    month = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=12,
    )


class MonthlyDonationReportView(APIView):
    """Return monthly donation totals grouped by category and currency."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        query_serializer = MonthlyDonationReportQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        filters = query_serializer.validated_data

        results = FinancialCalculationService.get_monthly_donation_report(
            year=filters["year"],
            month=filters["month"],
        )

        return Response(
            {
                "year": filters["year"],
                "month": filters["month"],
                "results": results,
            }
        )


class MonthlyIncomeReportView(APIView):
    """Return monthly confirmed donation and fund income by currency."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        query_serializer = MonthlyDonationReportQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        filters = query_serializer.validated_data

        results = FinancialCalculationService.get_monthly_income_report(
            year=filters["year"],
            month=filters["month"],
        )

        return Response(
            {
                "year": filters["year"],
                "month": filters["month"],
                "results": results,
            }
        )


class PendingFinancialReportView(APIView):
    """Return pending donations, fund transactions and adjustments."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        query_serializer = FinancialSummaryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        filters = query_serializer.validated_data

        records = get_pending_financial_records(
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
        )

        return Response(
            {
                "start_date": filters.get("start_date"),
                "end_date": filters.get("end_date"),
                "pending": {
                    "donations": DonationReportSerializer(
                        records["donations"],
                        many=True,
                    ).data,
                    "fund_transactions": FundTransactionReportSerializer(
                        records["fund_transactions"],
                        many=True,
                    ).data,
                    "adjustments": FinancialAdjustmentReportSerializer(
                        records["adjustments"],
                        many=True,
                    ).data,
                },
            }
        )


class DailyDonationReportQuerySerializer(serializers.Serializer):
    """Validate the date required for a daily donation report."""

    date = serializers.DateField(required=True)
