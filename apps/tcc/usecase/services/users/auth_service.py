# apps/tcc/controllers/auth_controller.py
from functools import wraps
from typing import Dict, Any
from wsgiref import validate
from apps.core.schemas.common.response import UserRegistrationResponse
from apps.core.schemas.schemas.users import UserCreateSchema, UserLoginSchema
from usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserAlreadyExistsException, 
    UserNotFoundException,
    InvalidCredentialsException,
    AccountLockedException
)
import logging

logger = logging.getLogger(__name__)

def handle_user_exceptions(func):
    """
    Decorator to handle user-related exceptions and convert to appropriate responses
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except UserAlreadyExistsException as e:
            logger.warning(f"User already exists: {e.details}")
            return UserRegistrationResponse.error_response(
                message="Registration failed",
                error_code="USER_ALREADY_EXISTS",
                status_code=409,
                details=e.details,
                user_message=e.user_message
            )
        except InvalidUserInputException as e:
            logger.warning(f"Invalid user input: {e.field_errors}")
            return UserRegistrationResponse.error_response(
                message="Validation failed",
                error_code="INVALID_INPUT",
                status_code=422,
                details={"field_errors": e.field_errors, **e.details},
                user_message=e.user_message
            )
        except InvalidCredentialsException as e:
            logger.warning(f"Invalid credentials: {e.details}")
            return UserRegistrationResponse.error_response(
                message="Authentication failed",
                error_code="INVALID_CREDENTIALS",
                status_code=401,
                details=e.details,
                user_message=e.user_message
            )
        except AccountLockedException as e:
            logger.warning(f"Account locked: {e.details}")
            return UserRegistrationResponse.error_response(
                message="Account locked",
                error_code="ACCOUNT_LOCKED",
                status_code=423,
                details=e.details,
                user_message=e.user_message
            )
        except UserNotFoundException as e:
            logger.warning(f"User not found: {e.details}")
            return UserRegistrationResponse.error_response(
                message="User not found",
                error_code="USER_NOT_FOUND",
                status_code=404,
                details=e.details,
                user_message=e.user_message
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return UserRegistrationResponse.error_response(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                status_code=500,
                details={"error": str(e)},
                user_message="An unexpected error occurred. Please try again later."
            )
    return wrapper

class AuthController:
    """Authentication controller with validation decorators and proper exception handling"""

    def __init__(self, create_user_uc, login_user_uc):
        self.create_user_uc = create_user_uc
        self.login_user_uc = login_user_uc

    @validate(schema_name="UserCreateSchema", data_key="user_data")
    @handle_user_exceptions
    async def register_user(self, user_data: dict):
        """
        Register user with automatic validation and exception handling
        """
        # Use case returns complete UserRegistrationResponse
        return await self.create_user_uc.execute(user_data)

    @validate(schema_name="UserLoginSchema", data_key="login_data")
    @handle_user_exceptions
    async def login_user(self, login_data: dict):
        """
        User login with validation and exception handling
        """
        return await self.login_user_uc.execute(login_data)

    @handle_user_exceptions
    async def get_user_profile(self, user_id: int):
        """
        Get user profile with exception handling
        """
        # This would use a GetUserUseCase
        return await self.get_user_uc.execute({"user_id": user_id})

    @validate(schema_name="UserUpdateSchema", data_key="update_data")
    @handle_user_exceptions
    async def update_user_profile(self, user_id: int, update_data: dict):
        """
        Update user profile with validation
        """
        # This would use an UpdateUserUseCase
        return await self.update_user_uc.execute({
            "user_id": user_id,
            "update_data": update_data
        })