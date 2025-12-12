from datetime import datetime
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Callable
from functools import wraps

from apps.core.core_exceptions.domain import NotFoundException
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    UnauthorizedActionException,
)
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
from apps.tcc.usecase.services.exceptions.auth_exceptions import AuthExceptionHandler

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseController:
    """
    Base controller for all controllers.
    Provides common functionality: error handling, validation, and use case execution.
    """
    
    def __init__(self):
        self._initialized = False
        self._use_cases: Dict[str, Any] = {}
    
    # ============ INITIALIZATION ============
    
    async def _initialize_use_cases(self, use_case_factories: Dict[str, Callable]):
        """
        Initialize multiple use cases using factory functions.
        
        Args:
            use_case_factories: Dict mapping use case names to factory functions
        """
        if self._initialized:
            return
            
        try:
            for name, factory in use_case_factories.items():
                self._use_cases[name] = await factory()
            self._initialized = True
            logger.info(f"Controller {self.__class__.__name__} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize controller {self.__class__.__name__}: {e}")
            raise
    
    def get_use_case(self, name: str) -> Any:
        """Get a use case by name."""
        if not self._initialized:
            raise RuntimeError(f"Controller {self.__class__.__name__} not initialized")
        if name not in self._use_cases:
            raise ValueError(f"Use case '{name}' not found in controller")
        return self._use_cases[name]
    
    # ============ COMMON VALIDATION ============
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Dict[str, list]:
        """
        Validate required fields in input data.
        
        Returns:
            Dict of field errors if any, empty dict if valid
        """
        errors = {}
        
        for field in required_fields:
            field_value = data.get(field)
            if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                errors[field] = [f"{field.replace('_', ' ').title()} is required"]
        
        return errors
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Simple email format validation."""
        if not isinstance(email, str):
            return False
        if '@' not in email or '.' not in email:
            return False
        # Basic validation - you might want to use a regex or email validator
        return True
    
    def build_context(self, request_data: Optional[Dict[str, Any]] = None, **extra_context) -> Dict[str, Any]:
        """
        Build execution context with request metadata.
        
        Args:
            request_data: Original request data
            **extra_context: Additional context values
            
        Returns:
            Context dictionary
        """
        context = {
            'timestamp': datetime.utcnow().isoformat(),
            'controller': self.__class__.__name__,
        }
        
        if request_data:
            # Add sanitized request data (exclude sensitive fields)
            sensitive_fields = {'password', 'token', 'refresh_token', 'access_token', 'current_password', 'new_password', 'confirm_password'}
            sanitized_data = {k: v for k, v in request_data.items() 
                            if k not in sensitive_fields}
            context['request_data'] = sanitized_data
        
        # Add extra context
        context.update(extra_context)
        
        return context
    
    # ============ EXECUTION HELPERS ============
    
    async def execute_use_case(self, use_case_name: str, input_data: Dict[str, Any], 
                               user: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a use case with standardized error handling.
        
        Args:
            use_case_name: Name of the use case to execute
            input_data: Input data for the use case
            user: Current user (if authenticated)
            context: Execution context
            
        Returns:
            Use case result
        """
        use_case = self.get_use_case(use_case_name)
        
        # Build context if not provided
        if context is None:
            context = self.build_context(input_data)
        
        try:
            logger.debug(f"Executing use case '{use_case_name}' for user: {getattr(user, 'id', 'Anonymous')}")
            result = await use_case.execute(input_data, user, context)
            logger.debug(f"Use case '{use_case_name}' executed successfully")
            return result
            
        except InvalidUserInputException as e:
            # Log validation errors at debug level
            logger.debug(f"Validation error in use case '{use_case_name}': {e}")
            raise
            
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in use case '{use_case_name}': {e}", exc_info=True)
            raise
    
    # ============ DECORATORS ============
    
    @staticmethod
    def handle_exceptions(func):
        """
        Decorator to handle exceptions in controller methods.
        Converts exceptions to appropriate response types.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except InvalidUserInputException as e:
                # Log validation errors (usually user input issues)
                logger.info(f"Invalid user input in {func.__name__}: {e}")
                raise
            except UnauthorizedActionException as e:
                logger.warning(f"Unauthorized action in {func.__name__}: {e}")
                raise
            except NotFoundException as e:
                logger.info(f"Resource not found in {func.__name__}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                # Re-raise to let the global exception handler deal with it
                raise
        return wrapper
    
    @staticmethod
    def require_authentication(func):
        """
        Decorator to ensure method is called with an authenticated user.
        """
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # The user is typically passed as 'current_user' keyword argument
            # or as the second positional argument after self
            user = None
            
            # Check kwargs first
            if 'current_user' in kwargs:
                user = kwargs['current_user']
            # Check args (self is args[0], user might be args[1])
            elif len(args) > 1:
                # Check if the second argument looks like a user object
                potential_user = args[1]
                if hasattr(potential_user, 'id') and hasattr(potential_user, 'email'):
                    user = potential_user
            
            if not user:
                raise UnauthorizedActionException(
                    message="Authentication required",
                    user_message="Please login to access this resource."
                )
            
            return await func(self, *args, **kwargs)
        return wrapper
    
    @staticmethod
    def validate_input(schema_class: Type[T]):
        """
        Decorator to validate input data against a Pydantic schema.
        
        Args:
            schema_class: Pydantic schema class to validate against
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(self, input_data: Dict[str, Any], *args, **kwargs):
                try:
                    # Validate input with Pydantic schema
                    validated_data = schema_class(**input_data)
                    # Call the original function with validated data
                    return await func(self, validated_data.dict(), *args, **kwargs)
                except Exception as e:
                    # Format validation errors
                    field_errors = {}
                    
                    # Check if it's a Pydantic ValidationError
                    if hasattr(e, 'errors'):
                        for error in e.errors():
                            # Get field path (could be nested: ['user', 'email'])
                            field_path = error.get('loc', [])
                            if field_path:
                                # Join nested fields with dot notation
                                field = '.'.join(str(f) for f in field_path)
                            else:
                                field = 'general'
                            
                            msg = error.get('msg', 'Validation error')
                            error_type = error.get('type', '')
                            
                            # Customize error messages
                            if error_type == 'value_error.missing':
                                field_name = field_path[-1] if field_path else 'field'
                                msg = f"{str(field_name).replace('_', ' ').title()} is required"
                            elif error_type == 'value_error.email':
                                msg = "Please enter a valid email address"
                            elif 'min_length' in error_type:
                                min_length = error.get('ctx', {}).get('limit_value', 1)
                                msg = f"Must be at least {min_length} character(s)"
                            
                            if field not in field_errors:
                                field_errors[field] = []
                            field_errors[field].append(msg)
                    else:
                        field_errors['general'] = [str(e)]
                    
                    raise InvalidUserInputException(
                        field_errors=field_errors,
                        user_message="Invalid input data. Please check your request."
                    )
            return wrapper
        return decorator


# Optional: Create a generic CRUD controller base
class CRUDBaseController(BaseController):
    """Base controller for CRUD operations."""
    
    async def create(self, input_data: Dict[str, Any], 
                     context: Optional[Dict[str, Any]] = None) -> Any:
        """Create a new resource."""
        return await self.execute_use_case('create_uc', input_data, None, context)
    
    async def get(self, resource_id: Any, 
                  context: Optional[Dict[str, Any]] = None) -> Any:
        """Get a resource by ID."""
        return await self.execute_use_case('get_uc', {'id': resource_id}, None, context)
    
    async def update(self, resource_id: Any, input_data: Dict[str, Any], 
                     context: Optional[Dict[str, Any]] = None) -> Any:
        """Update a resource."""
        data = {'id': resource_id, **input_data}
        return await self.execute_use_case('update_uc', data, None, context)
    
    async def delete(self, resource_id: Any, 
                     context: Optional[Dict[str, Any]] = None) -> Any:
        """Delete a resource."""
        return await self.execute_use_case('delete_uc', {'id': resource_id}, None, context)
    
    async def list(self, query_params: Optional[Dict[str, Any]] = None, 
                   context: Optional[Dict[str, Any]] = None) -> Any:
        """List resources with optional filtering."""
        return await self.execute_use_case('list_uc', query_params or {}, None, context)
    
    async def search(self, search_term: str, 
                     context: Optional[Dict[str, Any]] = None) -> Any:
        """Search resources."""
        return await self.execute_use_case('search_uc', {'search': search_term}, None, context)