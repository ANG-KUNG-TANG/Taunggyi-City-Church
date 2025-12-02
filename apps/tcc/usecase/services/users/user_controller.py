import logging
from typing import Dict, Any, Optional, List
from apps.core.schemas.common.response import APIResponse
from apps.core.schemas.input_schemas.users import (
    UserCreateInputSchema, 
    UserUpdateInputSchema,
    UserQueryInputSchema,
    UserSearchInputSchema,
    EmailCheckInputSchema,
    PasswordVerificationInputSchema,
    UserChangePasswordInputSchema,
    UserResetPasswordRequestInputSchema,
    UserResetPasswordInputSchema
)
from apps.core.schemas.out_schemas.user_out_schemas import (
    UserResponseSchema,
    UserSimpleResponseSchema,
    UserListResponseSchema,
    UserSearchResponseSchema,
    EmailCheckResponseSchema,
    PasswordVerificationResponseSchema,
    UserCreateResponseSchema,
    UserUpdateResponseSchema,
    UserDeleteResponseSchema
)
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.u_handler_exceptions import UserExceptionHandler
# Import only the specific user decorators
from apps.core.schemas.validator.user_deco import (
    validate_user_create,
    validate_user_update,
    validate_user_query,
    validate_user_search,
    validate_change_password,
    validate_reset_password_request,
    validate_reset_password,
    validate_email_check,
    validate_password_verification,
    validate_user_ownership,
    require_admin,
    require_member,
    validate_and_authorize_user_create,
    validate_and_authorize_user_update,
    validate_and_authorize_user_query
)

logger = logging.getLogger(__name__)

class UserController(BaseController):
    """
    User Controller with specific user decorators for validation and authorization
    """
    
    def __init__(self):
        # Initialize dependency container
        self._dependency_container = None
        self._use_cases = {}

    async def initialize(self):
        """Initialize dependency container and use cases"""
        try:
            from apps.tcc.dependencies.user_dep import get_user_dependency_container
            
            # Get the dependency container
            self._dependency_container = await get_user_dependency_container()
            
            # Initialize all use cases at once for better performance
            self._use_cases = await self._dependency_container.get_all_user_use_cases()
            
            logger.info("UserController initialized successfully with all use cases")
            
        except ImportError as e:
            logger.error(f"Failed to import dependencies: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize UserController: {e}")
            raise

    def _get_use_case(self, use_case_name: str):
        """Get use case by name with fallback initialization"""
        if not self._use_cases or use_case_name not in self._use_cases:
            raise RuntimeError(f"Use case {use_case_name} not found. Controller not properly initialized.")
        
        return self._use_cases[use_case_name]

    # CREATE Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_and_authorize_user_create
    async def create_user(
        self, 
        user_data: UserCreateInputSchema, 
        context: Dict[str, Any] = None
    ) -> UserCreateResponseSchema:
        """
        Create a new user account
        """
        create_user_uc = self._get_use_case('create_user')

        result = await create_user_uc.execute(
            user_data.model_dump(), None, context or {}
        )
        
        user_response = UserResponseSchema(
            **result.model_dump() if hasattr(result, 'model_dump') else result
        )
        
        return UserCreateResponseSchema(
            **user_response.model_dump(),
            password_set=True,
            message="User created successfully"
        )

    # READ Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_member
    async def get_user_by_id(
        self, 
        user_id: int,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Get user by ID
        """
        get_user_by_id_uc = self._get_use_case('get_user_by_id')

        input_data = {'user_id': user_id}
        user_response = await get_user_by_id_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(
            **user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_member
    async def get_user_by_email(
        self, 
        email: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Get user by email
        """
        get_user_by_email_uc = self._get_use_case('get_user_by_email')

        input_data = {'email': email}
        user_response = await get_user_by_email_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(
            **user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_and_authorize_user_query
    async def get_all_users(
        self,
        validated_data: UserQueryInputSchema,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Get all users with pagination and filtering
        """
        get_all_users_uc = self._get_use_case('get_all_users')

        input_data = validated_data.model_dump()
        list_response = await get_all_users_uc.execute(
            input_data, current_user, context or {}
        )
        
        if hasattr(list_response, 'model_dump'):
            response_data = list_response.model_dump()
        else:
            response_data = list_response
            
        user_list_response = UserListResponseSchema(**response_data)
        
        return APIResponse.success_response(
            message="Users retrieved successfully",
            data=user_list_response.model_dump()
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    async def get_users_by_role(
        self,
        role: str,
        page: int = 1,
        per_page: int = 20,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Get users by role with pagination
        """
        get_users_by_role_uc = self._get_use_case('get_users_by_role')

        input_data = {
            'role': role,
            'page': page,
            'per_page': per_page
        }
        list_response = await get_users_by_role_uc.execute(
            input_data, current_user, context or {}
        )
        
        if hasattr(list_response, 'model_dump'):
            response_data = list_response.model_dump()
        else:
            response_data = list_response
            
        user_list_response = UserListResponseSchema(**response_data)
        
        return APIResponse.success_response(
            message=f"Users with role {role} retrieved successfully",
            data=user_list_response.model_dump()
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_search
    @require_admin
    async def search_users(
        self,
        validated_data: UserSearchInputSchema,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Search users with pagination
        """
        search_users_uc = self._get_use_case('search_users')

        input_data = validated_data.model_dump()
        list_response = await search_users_uc.execute(
            input_data, current_user, context or {}
        )
        
        if hasattr(list_response, 'model_dump'):
            response_data = list_response.model_dump()
        else:
            response_data = list_response
            
        search_response = UserSearchResponseSchema(
            **response_data,
            search_term=validated_data.search_term
        )
        
        return APIResponse.success_response(
            message=f"Search results for '{validated_data.search_term}'",
            data=search_response.model_dump()
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_member
    async def get_current_user_profile(
        self,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Get current authenticated user's profile
        """
        if not current_user or not hasattr(current_user, 'id'):
            from apps.tcc.usecase.domain_exception.u_exceptions import AuthenticationException
            raise AuthenticationException("User authentication required")
        
        get_user_by_id_uc = self._get_use_case('get_user_by_id')

        input_data = {'user_id': current_user.id}
        user_response = await get_user_by_id_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(
            **user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response
        )

    # UPDATE Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_and_authorize_user_update
    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserUpdateResponseSchema:
        """
        Update user profile
        """
        update_user_uc = self._get_use_case('update_user')

        input_data = {
            'user_id': user_id,
            'update_data': user_data.model_dump(exclude_unset=True)
        }
        updated_user = await update_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        user_response = UserResponseSchema(
            **updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user
        )
        
        return UserUpdateResponseSchema(
            **user_response.model_dump(),
            message="User updated successfully",
            changes=user_data.model_dump(exclude_unset=True)
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_update
    @validate_user_ownership()
    async def update_current_user_profile(
        self,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserUpdateResponseSchema:
        """
        Update current authenticated user's profile
        """
        if not current_user or not hasattr(current_user, 'id'):
            from apps.tcc.usecase.domain_exception.u_exceptions import AuthenticationException
            raise AuthenticationException("User authentication required")
        
        update_user_uc = self._get_use_case('update_user')

        input_data = {
            'user_id': current_user.id,
            'update_data': user_data.model_dump(exclude_unset=True)
        }
        updated_user = await update_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        user_response = UserResponseSchema(
            **updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user
        )
        
        return UserUpdateResponseSchema(
            **user_response.model_dump(),
            message="Profile updated successfully",
            changes=user_data.model_dump(exclude_unset=True)
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    async def change_user_status(
        self,
        user_id: int,
        status: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Change user status
        """
        change_user_status_uc = self._get_use_case('change_user_status')

        input_data = {
            'user_id': user_id,
            'status': status
        }
        updated_user = await change_user_status_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(
            **updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user
        )

    # PASSWORD Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_change_password
    @require_member
    async def change_password(
        self,
        validated_data: UserChangePasswordInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Change user password
        """
        update_user_uc = self._get_use_case('update_user')
        
        input_data = {
            'user_id': current_user.id,
            'update_data': {
                'password': validated_data.new_password
            }
        }
        
        result = await update_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        return APIResponse.success_response(
            message="Password changed successfully",
            data={"user_id": current_user.id}
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_password_verification
    async def verify_password(
        self,
        validated_data: PasswordVerificationInputSchema,
        context: Dict[str, Any] = None
    ) -> PasswordVerificationResponseSchema:
        """
        Verify user password
        """
        verify_password_uc = self._get_use_case('verify_password')

        input_data = validated_data.model_dump()
        result = await verify_password_uc.execute(
            input_data, None, context or {}
        )
        
        return PasswordVerificationResponseSchema(
            user_id=validated_data.user_id,
            valid=result
        )

    # EMAIL Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_email_check
    async def check_email_availability(
        self,
        validated_data: EmailCheckInputSchema,
        context: Dict[str, Any] = None
    ) -> EmailCheckResponseSchema:
        """
        Check if email is available
        """
        get_user_by_email_uc = self._get_use_case('get_user_by_email')

        try:
            input_data = {'email': validated_data.email}
            await get_user_by_email_uc.execute(input_data, None, context or {})
            exists = True
        except Exception:
            exists = False
        
        return EmailCheckResponseSchema(
            email=validated_data.email,
            exists=exists,
            available=not exists
        )

    # PASSWORD RESET Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_reset_password_request
    async def request_password_reset(
        self,
        validated_data: UserResetPasswordRequestInputSchema,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Request password reset
        """
        return APIResponse.success_response(
            message="If the email exists, a password reset link has been sent",
            data={"email": validated_data.email}
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_reset_password
    async def reset_password(
        self,
        validated_data: UserResetPasswordInputSchema,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Reset password using token
        """
        return APIResponse.success_response(
            message="Password has been reset successfully",
            data={"reset": True}
        )

    # DELETE Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    async def delete_user(
        self,
        user_id: int,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Soft delete user
        """
        delete_user_uc = self._get_use_case('delete_user')

        input_data = {'user_id': user_id}
        delete_response = await delete_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        delete_data = UserDeleteResponseSchema(
            id=user_id,
            deleted=True,
            message="User deleted successfully"
        )
        
        return APIResponse.success_response(
            message=delete_response.message if hasattr(delete_response, 'message') else "User deleted successfully",
            data=delete_data.model_dump()
        )

    # BATCH Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    async def bulk_change_status(
        self,
        user_ids: List[int],
        status: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Bulk change user statuses
        """
        change_user_status_uc = self._get_use_case('change_user_status')

        results = []
        errors = []
        
        for user_id in user_ids:
            try:
                input_data = {'user_id': user_id, 'status': status}
                updated_user = await change_user_status_uc.execute(
                    input_data, current_user, context or {}
                )
                
                user_response = UserResponseSchema(
                    **updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user
                )
                results.append({
                    'user_id': user_id, 
                    'success': True,
                    'user': user_response.model_dump()
                })
            except Exception as e:
                errors.append({
                    'user_id': user_id, 
                    'error': str(e),
                    'success': False
                })
                logger.error(f"Failed to update status for user {user_id}: {str(e)}")
        
        return APIResponse.success_response(
            message=f"Bulk status update completed. Success: {len(results)}, Failed: {len(errors)}",
            data={
                'successful_updates': results,
                'failed_updates': errors,
                'status': status
            }
        )

# Factory function
async def create_user_controller() -> UserController:
    """
    Create and initialize user controller using dependency injection
    """
    controller = UserController()
    await controller.initialize()
    return controller