
from functools import wraps
import logging
from apps.core.schemas.common.response import APIResponse

logger = logging.getLogger(__name__)

class BaseController:
    """Provides centralized exception handling for controllers"""

    @staticmethod
    def handle_exceptions(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
                return APIResponse.error_response(
                    message="An unexpected error occurred.",
                    data={"error": str(e)}
                )
        return wrapper
