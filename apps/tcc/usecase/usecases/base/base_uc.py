import uuid
import logging
from django.db import transaction
from asgiref.sync import sync_to_async

from apps.core.core_exceptions.domain import DomainException
from .config import UseCaseConfiguration
from .base_context import OperationContext
from .authorization import AuthorizationManager
from usecase.domain_exception.u_exceptions import (
    UnauthorizedActionException,
    DomainValidationException
)

logger = logging.getLogger("app.usecase")


class BaseUseCase:
    """
    Base UseCase class for clean architecture.
    Features:
        - Async execution
        - Transaction support
        - Input/Output validation hooks
        - Auth & permission checks
        - Exception handling & logging
        - Context tracking
    """

    def __init__(self, **dependencies):
        self.config = UseCaseConfiguration()
        self._setup_configuration()
        # Inject dependencies dynamically
        for key, value in dependencies.items():
            setattr(self, key, value)

    # ------------------------------------------------------------------
    # Override this in each UC to configure
    # ------------------------------------------------------------------
    def _setup_configuration(self):
        """
        Example configuration:
            self.config.transactional = True
            self.config.require_authentication = True
            self.config.validate_input = True
            self.config.validate_output = True
        """
        pass

    # ------------------------------------------------------------------
    # Public async entry point
    # ------------------------------------------------------------------
    async def execute(self, input_data, user=None):
        ctx = OperationContext(
            operation_id=str(uuid.uuid4()),
            user=user,
            input_data=input_data
        )

        try:
            # Pre-execution: auth, authorization, input validation
            await self._before(ctx)

            # Execute main logic
            if self.config.transactional:
                async with transaction.async_atomic():
                    result = await self._on_execute(input_data, user, ctx)
            else:
                result = await self._on_execute(input_data, user, ctx)

            ctx.output_data = result

            # Post-execution: output validation
            await self._after(ctx)

            return result

        except DomainException:
            # Domain exceptions are safe, rethrow to controller
            raise

        except Exception as exc:
            # Convert technical exceptions into domain-safe exception
            ctx.error = exc
            raise await self._on_exception(exc, ctx)

        finally:
            ctx.end_time = uuid.uuid4()
            await self._finalize(ctx)

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    async def _before(self, ctx: OperationContext):
        """
        Pre-execution hook:
            - Authentication
            - Authorization
            - Input validation
        """
        if self.config.require_authentication and not ctx.user:
            raise UnauthorizedActionException("Authentication required")

        authorized = await sync_to_async(
            AuthorizationManager.is_authorized
        )(ctx.user, self.config)

        if not authorized:
            raise UnauthorizedActionException("You do not have permission")

        if self.config.validate_input:
            await self._validate_input(ctx.input_data, ctx)

    async def _after(self, ctx: OperationContext):
        """Post-execution hook: output validation"""
        if self.config.validate_output:
            await self._validate_output(ctx.output_data, ctx)

    async def _finalize(self, ctx: OperationContext):
        """Always runs: logging, cleanup, audit integration"""
        logger.info(
            f"[{self.__class__.__name__}] Completed with operation_id={ctx.operation_id}"
        )

    # ------------------------------------------------------------------
    # Methods to override in concrete UCs
    # ------------------------------------------------------------------
    async def _validate_input(self, input_data, ctx):
        """Override for input validation"""
        pass

    async def _validate_output(self, output_data, ctx):
        """Override for output validation"""
        pass

    async def _on_execute(self, input_data, user, ctx):
        """Override: main UC logic"""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _on_execute()")

    # ------------------------------------------------------------------
    # Exception handling
    # ------------------------------------------------------------------
    async def _on_exception(self, exc, ctx):
        """
        Convert unexpected errors into domain-safe exceptions
        """
        logger.error(
            f"[{self.__class__.__name__}] Unexpected error: {exc}",
            exc_info=True
        )
        return DomainValidationException(message="Internal server error")

# Backward compatibility alias
OperationPortalUseCase = BaseUseCase
