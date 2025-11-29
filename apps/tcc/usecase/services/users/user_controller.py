import logging
from typing import Dict, Any, Optional, List
from apps.core.schemas.common.response import APIResponse
from apps.core.schemas.input_schemas.u_input_schema import UserCreateInputSchema, UserUpdateInputSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.u_handler_exceptions import UserExceptionHandler
from apps.core.core_validators.decorators import (
    validate_user_create, validate_user_update, validate_user_query,
    require_admin, require_member
)

logger = logging.getLogger(__name__)

class UserController(BaseController):
    """
    User Controller with proper dependency injection and async operation
    """
    
    def __init__(self):
        # Initialize use cases as None, will be set via dependency injection
        self.create_user_uc = None
        self.get_user_by_id_uc = None
        self.get_user_by_email_uc = None
        self.get_all_users_uc = None
        self.get_users_by_role_uc = None
        self.search_users_uc = None
        self.update_user_uc = None
        self.change_user_status_uc = None
        self.delete_user_uc = None

    async def initialize(self):
        """Initialize use cases using dependency injection"""
        from apps.tcc.dependencies.user_dep import (
            get_create_user_uc, get_user_by_id_uc, get_user_by_email_uc,
            get_all_users_uc, get_users_by_role_uc, get_search_users_uc,
            get_update_user_uc, get_change_user_status_uc, get_delete_user_uc
        )
        
        self.create_user_uc = await get_create_user_uc()
        self.get_user_by_id_uc = await get_user_by_id_uc()
        self.get_user_by_email_uc = await get_user_by_email_uc()
        self.get_all_users_uc = await get_all_users_uc()
        self.get_users_by_role_uc = await get_users_by_role_uc()
        self.search_users_uc = await get_search_users_uc()
        self.update_user_uc = await get_update_user_uc()
        self.change_user_status_uc = await get_change_user_status_uc()
        self.delete_user_uc = await get_delete_user_uc()

    # CREATE Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_create
    async def create_user(
        self, 
        user_data: UserCreateInputSchema, 
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Create a new user account
        Input validated by @validate_user_create decorator
        """
        if not self.create_user_uc:
            await self.initialize()

        result = await self.create_user_uc.execute(
            user_data.model_dump(), None, context or {}
        )
        
        # Convert to UserResponseSchema
        return UserResponseSchema(**result.model_dump() if hasattr(result, 'model_dump') else result)

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
        if not self.get_user_by_id_uc:
            await self.initialize()

        input_data = {'user_id': user_id}
        user_response = await self.get_user_by_id_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(**user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response)

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
        if not self.get_user_by_email_uc:
            await self.initialize()

        input_data = {'email': email}
        user_response = await self.get_user_by_email_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(**user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response)

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    async def get_all_users(
        self,
        filters: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 20,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Get all users with pagination and filtering
        """
        if not self.get_all_users_uc:
            await self.initialize()

        input_data = {
            'filters': filters or {},
            'page': page,
            'per_page': per_page
        }
        list_response = await self.get_all_users_uc.execute(
            input_data, current_user, context or {}
        )
        
        return APIResponse.success_response(
            message="Users retrieved successfully",
            data=list_response.model_dump() if hasattr(list_response, 'model_dump') else list_response
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
        if not self.get_users_by_role_uc:
            await self.initialize()

        input_data = {
            'role': role,
            'page': page,
            'per_page': per_page
        }
        list_response = await self.get_users_by_role_uc.execute(
            input_data, current_user, context or {}
        )
        
        return APIResponse.success_response(
            message=f"Users with role {role} retrieved successfully",
            data=list_response.model_dump() if hasattr(list_response, 'model_dump') else list_response
        )

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @require_admin
    async def search_users(
        self,
        search_term: str,
        page: int = 1,
        per_page: int = 20,
        current_user: Any = None,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Search users with pagination
        """
        if not self.search_users_uc:
            await self.initialize()

        input_data = {
            'search_term': search_term,
            'page': page,
            'per_page': per_page
        }
        list_response = await self.search_users_uc.execute(
            input_data, current_user, context or {}
        )
        
        return APIResponse.success_response(
            message=f"Search results for '{search_term}'",
            data=list_response.model_dump() if hasattr(list_response, 'model_dump') else list_response
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
        
        if not self.get_user_by_id_uc:
            await self.initialize()

        input_data = {'user_id': current_user.id}
        user_response = await self.get_user_by_id_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(**user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response)

    # UPDATE Operations
    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_update
    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Update user profile
        """
        if not self.update_user_uc:
            await self.initialize()

        input_data = {
            'user_id': user_id,
            'update_data': user_data.model_dump(exclude_unset=True)
        }
        updated_user = await self.update_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(**updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user)

    @BaseController.handle_exceptions
    @UserExceptionHandler.handle_user_exceptions
    @validate_user_update
    async def update_current_user_profile(
        self,
        user_data: UserUpdateInputSchema,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> UserResponseSchema:
        """
        Update current authenticated user's profile
        """
        if not current_user or not hasattr(current_user, 'id'):
            from apps.tcc.usecase.domain_exception.u_exceptions import AuthenticationException
            raise AuthenticationException("User authentication required")
        
        if not self.update_user_uc:
            await self.initialize()

        input_data = {
            'user_id': current_user.id,
            'update_data': user_data.model_dump(exclude_unset=True)
        }
        updated_user = await self.update_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(**updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user)

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
        if not self.change_user_status_uc:
            await self.initialize()

        input_data = {
            'user_id': user_id,
            'status': status
        }
        updated_user = await self.change_user_status_uc.execute(
            input_data, current_user, context or {}
        )
        
        return UserResponseSchema(**updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user)

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
        if not self.delete_user_uc:
            await self.initialize()

        input_data = {'user_id': user_id}
        delete_response = await self.delete_user_uc.execute(
            input_data, current_user, context or {}
        )
        
        return APIResponse.success_response(
            message=delete_response.message if hasattr(delete_response, 'message') else "User deleted successfully",
            data=delete_response.model_dump() if hasattr(delete_response, 'model_dump') else delete_response
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
        if not self.change_user_status_uc:
            await self.initialize()

        results = []
        errors = []
        
        for user_id in user_ids:
            try:
                input_data = {'user_id': user_id, 'status': status}
                updated_user = await self.change_user_status_uc.execute(
                    input_data, current_user, context or {}
                )
                
                user_response = UserResponseSchema(**updated_user.model_dump() if hasattr(updated_user, 'model_dump') else updated_user)
                results.append({
                    'user_id': user_id, 
                    'success': True,
                    'user': user_response.model_dump() if hasattr(user_response, 'model_dump') else user_response
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
                'failed_updates': errors
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