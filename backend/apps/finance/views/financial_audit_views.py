"""Read-only API for financial audit history."""

from rest_framework.pagination import PageNumberPagination
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


class FinancialAuditPagination(PageNumberPagination):
    """Pagination for financial audit-history records."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


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

        paginator = FinancialAuditPagination()
        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        response_serializer = FinancialAuditHistoryReadSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(response_serializer.data)
