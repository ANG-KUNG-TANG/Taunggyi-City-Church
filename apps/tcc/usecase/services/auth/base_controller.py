from functools import wraps
import logging

# Domain-layer exceptions
from apps.core.core_exceptions.domain import (
    BusinessRuleException,
    EntityNotFoundException,
    DomainValidationException,
    DomainException
)

logger = logging.getLogger(__name__)


class BaseController:
    """
    Pure controller exception handler for Clean Architecture (Design A).

    Key rules:
    - Controller NEVER returns APIResponse.
    - Controller returns ONLY domain schemas.
    - Any error is raised upward as a domain exception.
    - The VIEW layer handles HTTP + APIResponse formatting.
    """

    @staticmethod
    def handle_exceptions(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Normal controller flow → return domain object
                return await func(*args, **kwargs)

            # -----------------------------
            # DOMAIN EXCEPTIONS (Expected)
            # -----------------------------
            except EntityNotFoundException as e:
                logger.warning(f"[NOT FOUND] {func.__name__}: {e}")
                raise e  
            except DomainValidationException as e:
                logger.warning(f"[VALIDATION ERROR] {func.__name__}: {e}")
                raise e

            except BusinessRuleException as e:
                logger.warning(f"[BUSINESS RULE FAILED] {func.__name__}: {e}")
                raise e

            # -----------------------------
            # UNEXPECTED ERRORS
            # -----------------------------
            except Exception as e:
                logger.error(
                    f"[UNEXPECTED ERROR] {func.__name__}: {str(e)}",
                    exc_info=True
                )
                # Wrap unexpected errors into a domain-safe error
                raise DomainException(
                    message="An unexpected error occurred.",
                    context={"error": str(e)}
                )

        return wrapper
