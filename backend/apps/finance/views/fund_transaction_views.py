"""REST API views for fund transactions."""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.models import FinancialCategory, FundTransaction
from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.serializers.fund_transaction_serializers import (
    FundTransactionCreateSerializer,
    FundTransactionReadSerializer,
    FundTransactionUpdateSerializer,
)
from apps.finance.services.fund_transaction_service import (
    FundTransactionService,
)
from apps.finance.views.utils import (
    get_correlation_id,
    raise_service_error,
)


class FundTransactionListCreateView(APIView):
    """List fund transactions or create a pending transaction."""

    permission_classes = [CanManageFinance]

    def get_queryset(self):
        queryset = FundTransaction.objects.select_related("category").all()

        record_status = self.request.query_params.get("status")
        category_id = self.request.query_params.get("category_id")
        transaction_type = self.request.query_params.get("transaction_type")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if record_status:
            queryset = queryset.filter(status=record_status)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)

        return queryset.order_by("-transaction_date", "-created_at")

    def get(self, request):
        records = self.get_queryset()
        serializer = FundTransactionReadSerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FundTransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        category_id = data.pop("category_id")

        category = get_object_or_404(
            FinancialCategory,
            pk=category_id,
        )

        try:
            transaction = FundTransactionService.create_transaction(
                actor=request.user,
                category=category,
                correlation_id=get_correlation_id(request),
                **data,
            )
        except ValidationError as error:
            raise_service_error(error)

        return Response(
            FundTransactionReadSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )


class FundTransactionDetailView(APIView):
    """Retrieve or update a fund transaction."""

    permission_classes = [CanManageFinance]

    def get_object(self, transaction_id):
        return get_object_or_404(
            FundTransaction.objects.select_related("category"),
            pk=transaction_id,
        )

    def get(self, request, transaction_id):
        transaction = self.get_object(transaction_id)
        return Response(FundTransactionReadSerializer(transaction).data)

    def patch(self, request, transaction_id):
        serializer = FundTransactionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updates = dict(serializer.validated_data)

        if "category_id" in updates:
            category_id = updates.pop("category_id")
            updates["category"] = get_object_or_404(
                FinancialCategory,
                pk=category_id,
            )

        try:
            transaction = FundTransactionService.update_pending_transaction(
                actor=request.user,
                transaction_id=transaction_id,
                updates=updates,
                correlation_id=get_correlation_id(request),
            )
        except ValidationError as error:
            raise_service_error(error)

        return Response(FundTransactionReadSerializer(transaction).data)
