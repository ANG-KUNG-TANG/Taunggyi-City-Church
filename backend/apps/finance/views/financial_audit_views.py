"""Read-only API for financial audit history."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.selectors.audit_selectors import (
    get_financial_audit_history,
)
from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.serializers.financial_audit_serializers import (
    FinancialAuditHistoryQuerySerializer,
    FinancialAuditHistoryReadSerializer,
)


class FinancialAuditHistoryView(APIView):
    """Retrieve immutable audit events for financial records."""

    permission_classes = [CanManageFinance]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        query_serializer = FinancialAuditHistoryQuerySerializer(
            data=request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        queryset = get_financial_audit_history(
            query_serializer.validated_data,
        )

        response_serializer = FinancialAuditHistoryReadSerializer(
            queryset,
            many=True,
        )

        return Response(response_serializer.data)
