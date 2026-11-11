"""REST API views for financial authorisation decisions."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.permissions.finance_permissions import CanManageFinance
from apps.finance.serializers.authorization_serializers import (
    FinancialAuthorizationReadSerializer,
    FinancialAuthorizationRequestSerializer,
)
from apps.finance.services.authorization_service import (
    FinancialAuthorizationService,
)
from apps.finance.views.utils import (
    get_correlation_id,
    raise_service_error,
)


class BaseFinancialAuthorizationView(APIView):
    """Shared authorisation decision handling."""

    permission_classes = [CanManageFinance]
    service_method = None

    def post(self, request, target_id):
        serializer = FinancialAuthorizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        correlation_id = data.pop("correlation_id", None)

        if correlation_id is None:
            correlation_id = get_correlation_id(request)

        try:
            decision_method = getattr(
                FinancialAuthorizationService,
                self.service_method,
            )

            authorization = decision_method(
                actor=request.user,
                target_id=target_id,
                **data,
                correlation_id=correlation_id,
            )
        except ValidationError as error:
            raise_service_error(error)

        return Response(FinancialAuthorizationReadSerializer(authorization).data)


class DonationAuthorizationView(BaseFinancialAuthorizationView):
    """Authorise or reject a donation."""

    service_method = "decide_donation"


class FundTransactionAuthorizationView(BaseFinancialAuthorizationView):
    """Authorise or reject a fund transaction."""

    service_method = "decide_fund_transaction"


class FinancialAdjustmentAuthorizationView(BaseFinancialAuthorizationView):
    """Authorise or reject a financial adjustment."""

    service_method = "decide_adjustment"
