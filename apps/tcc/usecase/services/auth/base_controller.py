from functools import wraps
import logging
from apps.core.schemas.common.response import APIResponse

# Domain-layer exceptions
from apps.core.core_exceptions.domain import (
    BusinessRuleException,
    EntityNotFoundException,
    DomainValidationException
)

logger = logging.getLogger(__name__)


class BaseController:
    """Centralized, clean-architecture aligned exception handler for controllers."""

    @staticmethod
    def handle_exceptions(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Normal flow
                return await func(*args, **kwargs)

            # -----------------------------
            # Domain Exceptions (Expected)
            # -----------------------------
            except EntityNotFoundException as e:
                logger.warning(f"[NOT FOUND] {func.__name__}: {e}")
                return APIResponse.error_response(
                    message=e.message,
                    data=e.context,
                    status_code=404
                )

            except DomainValidationException as e:
                logger.warning(f"[VALIDATION ERROR] {func.__name__}: {e}")
                return APIResponse.error_response(
                    message=e.message,
                    data=e.context,
                    status_code=422
                )

            except BusinessRuleException as e:
                logger.warning(f"[BUSINESS RULE ERROR] {func.__name__}: {e}")
                return APIResponse.error_response(
                    message=e.message,
                    data=e.context,
                    status_code=400
                )

            # -----------------------------
            # Unexpected Errors (Fail-safe)
            # -----------------------------
            except Exception as e:
                logger.error(
                    f"[UNEXPECTED ERROR] {func.__name__}: {str(e)}",
                    exc_info=True
                )
                return APIResponse.error_response(
                    message="An unexpected error occurred.",
                    data={"error": str(e)},
                    status_code=500
                )

        return wrapper
