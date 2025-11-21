from functools import wraps
from typing import Dict, Any
from apps.core.core_validators.decorators import validate, validate_query_params
from apps.core.schemas.common.response import (
    UserRegistrationResponse, 
    LoginResponse,
    LogoutResponse,
    make_login_response,
    make_logout_response,
    APIResponse
)
from apps.core.schemas.schemas.users import (
    UserCreateSchema, 
    UserUpdateSchema, 
    UserQuerySchema,
    UserLoginSchema,
    UserChangePasswordSchema
)
from usecase.domain_exception.u_exceptions import (
    InvalidUserInputException,
    UserNotFoundException,
    UserAlreadyExistsException,
    InvalidCredentialsException,
    AccountLockedException,
    InsufficientPermissionsException
)
import logging

logger = logging.getLogger(__name__)

def handle_user_exceptions(func):
    """
    Unified decorator to handle all user-related exceptions using your APIResponse
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except UserAlreadyExistsException as e:
            logger.warning(f"User already exists: {e.details}")
            return UserRegistrationResponse.error_response(
                message=e.user_message or "Registration failed",
                data=e.details
            )
        except UserNotFoundException as e:
            logger.warning(f"User not found: {e.details}")
            return APIResponse.error_response(
                message=e.user_message or "User not found",
                data=e.details
            )
        except InvalidCredentialsException as e:
            logger.warning(f"Invalid credentials: {e.details}")
            return LoginResponse.error_response(
                message=e.user_message or "Authentication failed",
                data=e.details
            )
        except AccountLockedException as e:
            logger.warning(f"Account locked: {e.details}")
            return APIResponse.error_response(
                message=e.user_message or "Account locked",
                data=e.details
            )
        except InsufficientPermissionsException as e:
            logger.warning(f"Insufficient permissions: {e.details}")
            return APIResponse.error_response(
                message=e.user_message or "Permission denied",
                data=e.details
            )
        except InvalidUserInputException as e:
            logger.warning(f"Invalid user input: {e.field_errors}")
            return APIResponse.error_response(
                message=e.user_message or "Validation failed",
                data={
                    "field_errors": e.field_errors,
                    "details": e.details
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return APIResponse.error_response(
                message="An unexpected error occurred. Please try again later.",
                data={"error": str(e)}
            )
    return wrapper

class UserController:
    """
    Unified controller using your existing response schemas
    """

    def __init__(self, create_user_uc, get_user_uc, update_user_uc, 
                 list_users_uc, login_user_uc, change_password_uc):
        self.create_user_uc = create_user_uc
        self.get_user_uc = get_user_uc
        self.update_user_uc = update_user_uc
        self.list_users_uc = list_users_uc
        self.login_user_uc = login_user_uc
        self.change_password_uc = change_password_uc

    # Authentication endpoints
    @validate(schema_name="UserCreateSchema", data_key="user_data")
    @handle_user_exceptions
    async def register(self, user_data: dict) -> UserRegistrationResponse:
        """Register new user - returns UserRegistrationResponse"""
        return await self.create_user_uc.execute(user_data)

    @validate(schema_name="UserLoginSchema", data_key="login_data")
    @handle_user_exceptions
    async def login(self, login_data: dict) -> LoginResponse:
        """User login - returns LoginResponse"""
        # This assumes your login use case returns the proper format for make_login_response
        result = await self.login_user_uc.execute(login_data)
        
        # If the use case returns a dict with tokens and user, use make_login_response
        if isinstance(result, dict) and 'tokens' in result:
            return make_login_response(
                access_token=result['tokens'].get('access_token'),
                refresh_token=result['tokens'].get('refresh_token'),
                expires_in=result['tokens'].get('expires_in'),
                user=result.get('user'),
                message="Login successful"
            )
        return result

    @handle_user_exceptions
    async def logout(self) -> LogoutResponse:
        """User logout - returns LogoutResponse"""
        return make_logout_response("Logout successful")

    # User management endpoints
    @handle_user_exceptions
    async def get_profile(self, user_id: int) -> APIResponse:
        """Get user profile"""
        return await self.get_user_uc.execute({"user_id": user_id})

    @validate(schema_name="UserUpdateSchema", data_key="update_data")
    @handle_user_exceptions
    async def update_profile(self, user_id: int, update_data: dict) -> APIResponse:
        """Update user profile"""
        return await self.update_user_uc.execute({
            "user_id": user_id,
            "update_data": update_data
        })

    @validate(schema_name="UserChangePasswordSchema", data_key="password_data")
    @handle_user_exceptions
    async def change_password(self, user_id: int, password_data: dict) -> APIResponse:
        """Change user password"""
        return await self.change_password_uc.execute({
            "user_id": user_id,
            "password_data": password_data
        })

    @validate_query_params(schema_name="UserQuerySchema")
    @handle_user_exceptions
    async def list_users(self, validated_query: dict) -> APIResponse:
        """List users (admin only)"""
        return await self.list_users_uc.execute(validated_query)