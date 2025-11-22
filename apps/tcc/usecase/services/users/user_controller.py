# apps/tcc/controllers/user_controller.py
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
from apps.core.schemas.builders.builder import UserResponseBuilder
from apps.tcc.usecase.services.users.exception import UserExceptionHandler

# Use the production-level exception handler
handle_user_exceptions = UserExceptionHandler.handle_user_exceptions


class UserController:
    """
    Unified controller using comprehensive exception handling and response builders
    """

    def __init__(self, create_user_uc, get_user_uc, update_user_uc, 
                 list_users_uc, login_user_uc, change_password_uc, logout_user_uc=None):
        self.create_user_uc = create_user_uc
        self.get_user_uc = get_user_uc
        self.update_user_uc = update_user_uc
        self.list_users_uc = list_users_uc
        self.login_user_uc = login_user_uc
        self.change_password_uc = change_password_uc
        self.logout_user_uc = logout_user_uc

    # Authentication endpoints
    @validate(schema_name="UserCreateSchema", data_key="user_data")
    @handle_user_exceptions
    async def register(self, user_data: dict) -> UserRegistrationResponse:
        """
        Register new user with comprehensive validation and exception handling
        
        Args:
            user_data: Validated user creation data
            
        Returns:
            UserRegistrationResponse with user data and tokens
        """
        return await self.create_user_uc.execute(user_data)

    @validate(schema_name="UserLoginSchema", data_key="login_data")
    @handle_user_exceptions
    async def login(self, login_data: dict) -> LoginResponse:
        """
        User login with credential validation
        
        Args:
            login_data: Validated login credentials
            
        Returns:
            LoginResponse with access tokens and user info
        """
        result = await self.login_user_uc.execute(login_data)
        
        # Handle different response formats from use case
        if isinstance(result, dict):
            # If use case returns raw data, format it properly
            return make_login_response(
                access_token=result.get('access_token'),
                refresh_token=result.get('refresh_token'),
                expires_in=result.get('expires_in'),
                user=result.get('user'),
                message=result.get('message', 'Login successful')
            )
        elif hasattr(result, 'data') and isinstance(result.data, dict):
            # If use case returns APIResponse with data
            data = result.data
            return make_login_response(
                access_token=data.get('access_token'),
                refresh_token=data.get('refresh_token'),
                expires_in=data.get('expires_in'),
                user=data.get('user'),
                message=result.message or 'Login successful'
            )
        
        return result

    @handle_user_exceptions
    async def logout(self, user_id: int = None, token: str = None) -> LogoutResponse:
        """
        User logout with optional token invalidation
        
        Args:
            user_id: Optional user ID for targeted logout
            token: Optional specific token to invalidate
            
        Returns:
            LogoutResponse confirming logout
        """
        if self.logout_user_uc:
            # Use the logout use case if available
            await self.logout_user_uc.execute({
                'user_id': user_id,
                'token': token
            })
        
        return make_logout_response("Logout successful")

    # User management endpoints
    @handle_user_exceptions
    async def get_profile(self, user_id: int) -> APIResponse:
        """
        Get user profile by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            APIResponse with user profile data
        """
        return await self.get_user_uc.execute({"user_id": user_id})

    @validate(schema_name="UserUpdateSchema", data_key="update_data")
    @handle_user_exceptions
    async def update_profile(self, user_id: int, update_data: dict) -> APIResponse:
        """
        Update user profile with validation
        
        Args:
            user_id: User identifier
            update_data: Validated update data
            
        Returns:
            APIResponse with updated user data
        """
        return await self.update_user_uc.execute({
            "user_id": user_id,
            "update_data": update_data
        })

    @validate(schema_name="UserChangePasswordSchema", data_key="password_data")
    @handle_user_exceptions
    async def change_password(self, user_id: int, password_data: dict) -> APIResponse:
        """
        Change user password with security validation
        
        Args:
            user_id: User identifier
            password_data: Validated password change data
            
        Returns:
            APIResponse confirming password change
        """
        return await self.change_password_uc.execute({
            "user_id": user_id,
            "password_data": password_data
        })

    @validate_query_params(schema_name="UserQuerySchema")
    @handle_user_exceptions
    async def list_users(self, validated_query: dict) -> APIResponse:
        """
        List users with filtering and pagination
        
        Args:
            validated_query: Validated query parameters
            
        Returns:
            APIResponse with paginated user list
        """
        return await self.list_users_uc.execute(validated_query)

    @handle_user_exceptions
    async def get_current_user(self, current_user_id: int) -> APIResponse:
        """
        Get current authenticated user's profile
        
        Args:
            current_user_id: Authenticated user's ID from JWT
            
        Returns:
            APIResponse with current user data
        """
        return await self.get_user_uc.execute({"user_id": current_user_id})

    @validate(schema_name="UserUpdateSchema", data_key="update_data")
    @handle_user_exceptions
    async def update_current_user(self, current_user_id: int, update_data: dict) -> APIResponse:
        """
        Update current authenticated user's profile
        
        Args:
            current_user_id: Authenticated user's ID
            update_data: Validated update data
            
        Returns:
            APIResponse with updated user data
        """
        return await self.update_user_uc.execute({
            "user_id": current_user_id,
            "update_data": update_data
        })

    # Admin-only endpoints
    @handle_user_exceptions
    async def deactivate_user(self, user_id: int, current_user_id: int) -> APIResponse:
        """
        Deactivate user account (admin only)
        
        Args:
            user_id: User to deactivate
            current_user_id: Admin user ID for authorization
            
        Returns:
            APIResponse confirming deactivation
        """
        return await self.update_user_uc.execute({
            "user_id": user_id,
            "update_data": {"status": "INACTIVE"},
            "requester_id": current_user_id
        })

    @handle_user_exceptions
    async def activate_user(self, user_id: int, current_user_id: int) -> APIResponse:
        """
        Activate user account (admin only)
        
        Args:
            user_id: User to activate
            current_user_id: Admin user ID for authorization
            
        Returns:
            APIResponse confirming activation
        """
        return await self.update_user_uc.execute({
            "user_id": user_id,
            "update_data": {"status": "ACTIVE"},
            "requester_id": current_user_id
        })


# Factory function for dependency injection
def create_user_controller(
    create_user_uc,
    get_user_uc, 
    update_user_uc,
    list_users_uc,
    login_user_uc,
    change_password_uc,
    logout_user_uc=None
) -> UserController:
    """
    Factory function to create UserController with all dependencies
    
    Returns:
        Configured UserController instance
    """
    return UserController(
        create_user_uc=create_user_uc,
        get_user_uc=get_user_uc,
        update_user_uc=update_user_uc,
        list_users_uc=list_users_uc,
        login_user_uc=login_user_uc,
        change_password_uc=change_password_uc,
        logout_user_uc=logout_user_uc
    )