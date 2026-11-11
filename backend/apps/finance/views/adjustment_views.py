"""REST API views for financial adjustments."""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.models import (
    Donation,
    FinancialAdjustment,
    FundTransaction,
)
from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.serializers.adjustment_serializers import (
    FinancialAdjustmentCreateSerializer,
    FinancialAdjustmentReadSerializer,
    FinancialAdjustmentUpdateSerializer,
)
from apps.finance.services.financial_adjustment_service import (
    FinancialAdjustmentService,
)
from apps.finance.views.utils import (
    get_correlation_id,
    raise_service_error,
)


class FinancialAdjustmentListCreateView(APIView):
    """List adjustments or create a pending adjustment."""

    permission_classes = [CanManageFinance]

    def get(self, request):
        queryset = FinancialAdjustment.objects.select_related(
            "donation",
            "fund_transaction",
            "created_by",
            "updated_by",
        ).all()

        record_status = request.query_params.get("status")
        adjustment_type = request.query_params.get("adjustment_type")
        donation_id = request.query_params.get("donation_id")
        fund_transaction_id = request.query_params.get("fund_transaction_id")

        if record_status:
            queryset = queryset.filter(status=record_status)

        if adjustment_type:
            queryset = queryset.filter(adjustment_type=adjustment_type)

        if donation_id:
            queryset = queryset.filter(donation_id=donation_id)

        if fund_transaction_id:
            queryset = queryset.filter(fund_transaction_id=fund_transaction_id)

        queryset = queryset.order_by("-created_at")

        serializer = FinancialAdjustmentReadSerializer(
            queryset,
            many=True,
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = FinancialAdjustmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        donation_id = data.get("donation_id")
        fund_transaction_id = data.get("fund_transaction_id")

        if donation_id:
            get_object_or_404(Donation, pk=donation_id)

        if fund_transaction_id:
            get_object_or_404(FundTransaction, pk=fund_transaction_id)

        try:
            adjustment = FinancialAdjustmentService.create_adjustment(
                actor=request.user,
                correlation_id=get_correlation_id(request),
                **data,
            )
        except (
            ValidationError,
            Donation.DoesNotExist,
            FundTransaction.DoesNotExist,
        ) as error:
            if isinstance(error, (Donation.DoesNotExist, FundTransaction.DoesNotExist)):
                from rest_framework.exceptions import NotFound

                raise NotFound("The financial target does not exist.")

            raise_service_error(error)

        return Response(
            FinancialAdjustmentReadSerializer(adjustment).data,
            status=status.HTTP_201_CREATED,
        )


class FinancialAdjustmentDetailView(APIView):
    """Retrieve or update a pending financial adjustment."""

    permission_classes = [CanManageFinance]

    def get_object(self, adjustment_id):
        return get_object_or_404(
            FinancialAdjustment.objects.select_related(
                "donation",
                "fund_transaction",
                "created_by",
                "updated_by",
            ),
            pk=adjustment_id,
        )

    def get(self, request, adjustment_id):
        adjustment = self.get_object(adjustment_id)

        return Response(FinancialAdjustmentReadSerializer(adjustment).data)

    def patch(self, request, adjustment_id):
        serializer = FinancialAdjustmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            adjustment = FinancialAdjustmentService.update_pending_adjustment(
                actor=request.user,
                adjustment_id=adjustment_id,
                correlation_id=get_correlation_id(request),
                **serializer.validated_data,
            )
        except FinancialAdjustment.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("The financial adjustment does not exist.")
        except ValidationError as error:
            raise_service_error(error)

        return Response(FinancialAdjustmentReadSerializer(adjustment).data)
