from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework import status
from typing import Dict, Any, Tuple


class BaseView:
    """
    Base class for all API endpoints.
    Contains shared HTTP-related utilities only.
    """

    def build_context(self, request: Request) -> Dict[str, Any]:
        """Convert DRF request → context dict for controller."""
        return {
            "ip": self._get_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "method": request.method,
            "path": request.path,
            "request": request,
        }

    def _get_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def map_controller_status(self, result, http_method: str = "GET") -> int:
        """
        Map controller's APIResponse → appropriate HTTP status code.
        """
        if not hasattr(result, 'success'):
            return status.HTTP_500_INTERNAL_SERVER_ERROR
            
        if result.success:
            # Map success responses based on HTTP method
            if http_method == "POST":
                return status.HTTP_201_CREATED
            elif http_method == "DELETE":
                return status.HTTP_204_NO_CONTENT
            else:  # GET, PUT, PATCH
                return status.HTTP_200_OK
        else:
            return status.HTTP_400_BAD_REQUEST

    def extract_filters(self, request: Request) -> Dict[str, Any]:
        """Standardised query filters for list endpoints."""
        allowed = ["status", "role", "is_active", "created_after", "created_before"]
        return {k: v for k, v in request.query_params.items() if k in allowed}

    def get_pagination_params(self, request: Request) -> Tuple[int, int]:
        """Extract and validate pagination parameters."""
        try:
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))
            page = max(1, page)
            per_page = max(1, min(per_page, 100))
            return page, per_page
        except (TypeError, ValueError):
            return 1, 20

    def create_response(self, result, http_method: str = "GET") -> Response:
        """Create standardized DRF Response from controller result."""
        status_code = self.map_controller_status(result, http_method)
        return Response(result.data, status=status_code)