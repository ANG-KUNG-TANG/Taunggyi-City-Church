"""REST API views for financial donations."""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.models import Donation, FinancialCategory
from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.serializers.donation_serializers import (
    DonationCreateSerializer,
    DonationReadSerializer,
    DonationUpdateSerializer,
)
from apps.finance.services.donation_service import DonationService
from apps.finance.views.utils import (
    get_correlation_id,
    raise_service_error,
)


class DonationListCreateView(APIView):
    """List donations or create a pending donation."""

    permission_classes = [CanManageFinance]

    def get_queryset(self):
        queryset = Donation.objects.select_related("category").all()

        record_status = self.request.query_params.get("status")
        category_id = self.request.query_params.get("category_id")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if record_status:
            queryset = queryset.filter(status=record_status)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(transaction_date__lte=end_date)

        return queryset.order_by("-transaction_date", "-created_at")

    def get(self, request):
        records = self.get_queryset()
        serializer = DonationReadSerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DonationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        category_id = data.pop("category_id")

        category = get_object_or_404(
            FinancialCategory,
            pk=category_id,
        )

        try:
            donation = DonationService.create_donation(
                actor=request.user,
                category=category,
                correlation_id=get_correlation_id(request),
                **data,
            )
        except ValidationError as error:
            raise_service_error(error)

        return Response(
            DonationReadSerializer(donation).data,
            status=status.HTTP_201_CREATED,
        )


class DonationDetailView(APIView):
    """Retrieve or update a donation."""

    permission_classes = [CanManageFinance]

    def get_object(self, donation_id):
        return get_object_or_404(
            Donation.objects.select_related("category"),
            pk=donation_id,
        )

    def get(self, request, donation_id):
        donation = self.get_object(donation_id)
        return Response(DonationReadSerializer(donation).data)

    def patch(self, request, donation_id):
        serializer = DonationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updates = dict(serializer.validated_data)

        if "category_id" in updates:
            category_id = updates.pop("category_id")
            updates["category"] = get_object_or_404(
                FinancialCategory,
                pk=category_id,
            )

        try:
            donation = DonationService.update_pending_donation(
                actor=request.user,
                donation_id=donation_id,
                updates=updates,
                correlation_id=get_correlation_id(request),
            )
        except ValidationError as error:
            raise_service_error(error)

        return Response(DonationReadSerializer(donation).data)
