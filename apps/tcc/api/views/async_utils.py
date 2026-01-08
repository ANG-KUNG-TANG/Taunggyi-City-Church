"""
Standard DRF views - Remove custom async complexity
"""
from rest_framework.views import APIView
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


class StandardAPIView(APIView):
    """
    Standard DRF APIView - Use Django's built-in async support if needed
    """
    # This is just a standard APIView
    # Let DRF handle request/response lifecycle
    pass