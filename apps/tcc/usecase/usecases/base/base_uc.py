from typing import Any, Optional, Dict, List
from django.db import transaction
from django.contrib.auth import get_user_model
import logging
import uuid
from datetime import datetime

# from core.exception_deal.exception_handler.portal_exception import DomainException
from usecase.exceptions.u_exceptions import DomainException, UnauthorizedActionException
from usecase.repo.users.user_repo import UserRepository
from usecase.entities.users import UserEntity

logger = logging.getLogger('tcc.usecase')
User = get_user_model()

class UseCaseConfiguration:
    """Configuration for usecase execution"""
    
    def __init__(self):
        self.require_authentication = True
        self.required_permissions: List[str] = []
        self.required_roles: List[str] = []
        self.audit_log = True
        self.validate_input = True
        self.validate_output = True
        self.transactional = True
        self.timeout_seconds = 30

class OperationContext:
    """Context for operation execution"""
    
    def __init__(self):
        self.operation_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        self.execution_time = None
        self.user: Optional[UserEntity] = None
        self.input_data: Any = None
        self.output_data: Any = None
        self.error: Optional[Exception] = None
        self.metadata: Dict[str, Any] = {}

class AuthorizationManager:
    """Handles authorization checks using User entity"""
    
    @staticmethod
    def is_authorized(user: Optional[UserEntity], config: UseCaseConfiguration) -> bool:
        """Check if user is authorized for the operation"""
        # If no authentication required, allow
        if not config.require_authentication:
            return True
            
        # Check if user is authenticated
        if not user:
            return False
            
        # Check if user is active
        if not user.is_active:
            return False
            
        # Check role-based authorization
        if config.required_roles and user.role not in config.required_roles:
            return False
            
        # Check permission-based authorization
        if config.required_permissions:
            user_permissions = user.get_permissions()
            return all(user_permissions.get(perm, False) for perm in config.required_permissions)
            
        return True

class OperationPortalUseCase:
    """
    Base usecase class that handles cross-cutting concerns using User entity
    """
    
    def __init__(self, user_repository: UserRepository = None):
        self.user_repository = user_repository or UserRepository()
        self.config = UseCaseConfiguration()
        self._setup_configuration()
        
    def _setup_configuration(self):
        """Setup usecase-specific configuration - override in subclasses"""
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("UseCase", "")

    def execute(self, input_data: Any, user: Optional[UserEntity] = None) -> Any:
        """
        Main execution method with built-in cross-cutting concerns
        """
        context = OperationContext()
        context.start_time = datetime.utcnow()
        context.user = user
        context.input_data = input_data
        
        try:
            # Pre-execution phase
            self._before_execute(context)
            
            # Core execution phase
            if self.config.transactional:
                with transaction.atomic():
                    output = self._on_execute(input_data, user, context)
            else:
                output = self._on_execute(input_data, user, context)
            
            # Post-execution phase
            context.output_data = output
            self._after_execute(context)
            
            return output
            
        except DomainException:
            raise
        except Exception as exc:
            context.error = exc
            raise self._on_exception(exc, context)
        finally:
            # Finalize operation context
            context.end_time = datetime.utcnow()
            context.execution_time = (context.end_time - context.start_time).total_seconds()
            self._finalize_operation(context)

    def _before_execute(self, context: OperationContext) -> None:
        """Pre-execution hooks - authentication, authorization, validation"""
        
        # Authentication check
        if self.config.require_authentication and not context.user:
            raise UnauthorizedActionException(
                error_code=None,
                message=f"Authentication required for action: {self.name}",
                details={"action": self.name}
            )
        
        # User active check
        if self.config.require_authentication and context.user and not context.user.is_active:
            raise UnauthorizedActionException(
                error_code=None,
                message="User account is inactive",
                details={
                    "user_id": context.user.id,
                    "username": context.user.name,
                    "action": self.name
                }
            )
        
        # Authorization check
        if not AuthorizationManager.is_authorized(context.user, self.config):
            user_id = context.user.id if context.user else "anonymous"
            user_name = context.user.name if context.user else "anonymous"
            
            raise UnauthorizedActionException(
                error_code=None,
                message=f"User '{user_name}' is NOT authorized for action: {self.name}",
                details={
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_role": context.user.role if context.user else "anonymous",
                    "action": self.name,
                    "required_roles": self.config.required_roles,
                    "required_permissions": self.config.required_permissions
                }
            )
        
        # Input validation
        if self.config.validate_input:
            self._validate_input(context.input_data, context)
        
        # Audit log - operation start
        if self.config.audit_log:
            logger.info(
                f"Operation started: {self.name} "
                f"(ID: {context.operation_id}, User: {context.user.name if context.user else 'anonymous'})"
            )

    def _after_execute(self, context: OperationContext) -> None:
        """Post-execution hooks - output validation, side effects"""
        
        # Output validation
        if self.config.validate_output:
            self._validate_output(context.output_data, context)
        
        # Additional post-execution logic
        self._on_after_execute(context.output_data, context)

    def _on_after_execute(self, output: Any, context: OperationContext) -> None:
        """Override for custom post-execution logic"""
        pass

    def _on_exception(self, exception: Exception, context: OperationContext) -> DomainException:
        """Handle exceptions and convert to DomainException"""
        
        # Log the exception
        logger.error(
            f"Operation failed: {self.name} "
            f"(ID: {context.operation_id}, User: {context.user.name if context.user else 'anonymous'}, Error: {str(exception)})",
            exc_info=True
        )
        
        # Convert to DomainException
        error_code = getattr(exception, 'error_code', None)
        if error_code is None:
            from helpers.exceptions.domain.error_codes import ErrorCode
            error_code = ErrorCode.SYSTEM_ERROR

        return DomainException(
            error_code=error_code,
            message=str(exception),
            details={
                "original_exception": str(exception),
                "operation_id": context.operation_id,
                "action": self.name,
                "user_id": context.user.id if context.user else None
            },
            http_status=500
        )

    def _finalize_operation(self, context: OperationContext) -> None:
        """Finalize operation with audit logging"""
        if self.config.audit_log:
            status = "FAILED" if context.error else "COMPLETED"
            user_info = context.user.name if context.user else "anonymous"
            logger.info(
                f"Operation {status}: {self.name} "
                f"(ID: {context.operation_id}, User: {user_info}, Duration: {context.execution_time:.2f}s)"
            )

    def _validate_input(self, input_data: Any, context: OperationContext) -> None:
        """Validate input data - override in subclasses"""
        pass

    def _validate_output(self, output_data: Any, context: OperationContext) -> None:
        """Validate output data - override in subclasses"""
        pass

    def _on_execute(self, input_data: Any, user: Optional[UserEntity], context: OperationContext) -> Any:
        """Core execution logic - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _on_execute()")