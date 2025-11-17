import uuid
import logging
from django.db import transaction

from apps.core.core_exceptions.domain import DomainException
from .config import UseCaseConfiguration
from .base_context import OperationContext
from .authorization import AuthorizationManager
from usecase.domain_exception.u_exceptions import UnauthorizedActionException

logger = logging.getLogger("app.usecase")

class BaseUseCase:
    def __init__(self, **dependencies):
        self.config = UseCaseConfiguration()
        self._setup_configuration()
        self.__dict__.update(dependencies)

    def _setup_configuration(self):
        pass

    def execute(self, input_data, user=None):
        context = OperationContext(operation_id=str(uuid.uuid4()),
                                   user=user,
                                   input_data=input_data)

        try:
            self._before(context)

            if self.config.transactional:
                with transaction.atomic():
                    result = self._on_execute(input_data, user, context)
            else:
                result = self._on_execute(input_data, user, context)

            context.output_data = result
            self._after(context)
            return result

        except DomainException:
            raise

        except Exception as exc:
            context.error = exc
            raise self._on_exception(exc, context)

        finally:
            context.end_time = uuid.uuid4()
            self._finalize(context)

    # ---------------- Core Hooks -----------------

    def _before(self, ctx: OperationContext):
        if self.config.require_authentication and not ctx.user:
            raise UnauthorizedActionException(message="Authentication required")

        if not AuthorizationManager.is_authorized(ctx.user, self.config):
            raise UnauthorizedActionException(message="Unauthorized")

        if self.config.validate_input:
            self._validate_input(ctx.input_data, ctx)

    def _after(self, ctx: OperationContext):
        if self.config.validate_output:
            self._validate_output(ctx.output_data, ctx)

    # Methods to override
    def _validate_input(self, input_data, ctx): pass
    def _validate_output(self, output_data, ctx): pass
    def _on_after_execute(self, result, ctx): pass
    def _on_execute(self, input_data, user, ctx): raise NotImplementedError()

    # Exception Formatting
    def _on_exception(self, exc, ctx):
        logger.error(f"UseCase Error in {self.__class__.__name__}: {exc}")
        return DomainException(message=str(exc))

    def _finalize(self, ctx):
        logger.info(f"[{self.__class__.__name__}] Completed.")
