"""Protected financial reporting API views."""

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.services.financial_calculation_service import (
    FinancialCalculationService,
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
