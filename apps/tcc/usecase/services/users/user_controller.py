import logging
from typing import Dict, Any, Optional, List
from apps.core.schemas.common.response import APIResponse
from apps.core.schemas.builders.user_rp_builder import UserResponseBuilder
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.tcc.usecase.services.exceptions.u_handler_exceptions import UserExceptionHandler
from apps.tcc.usecase.usecases.users.user_create_uc import CreateUserUseCase
from apps.tcc.usecase.usecases.users.user_read_uc import (
    GetUserByIdUseCase,
    GetUserByEmailUseCase,
    GetAllUsersUseCase,
    GetUsersByRoleUseCase,
    SearchUsersUseCase
)
from apps.tcc.usecase.usecases.users.user_update_uc import UpdateUserUseCase, ChangeUserStatusUseCase
from apps.tcc.usecase.usecases.users.user_delete_uc import DeleteUserUseCase
from apps.core.core_validators.decorators import validate
from apps.core.schemas.schemas.users import UserCreateSchema, UserUpdateSchema
from apps.tcc.models.base.enums import UserRole, UserStatus

logger = logging.getLogger(__name__)


class UserController(BaseController):
    """
    User Controller with Dependency Injected Use Cases
    Now properly integrated with your dependency injection system
    """
    
    def __init__(
        self,
        create_user_uc: CreateUserUseCase,
        get_user_by_id_uc: GetUserByIdUseCase,
        get_user_by_email_uc: GetUserByEmailUseCase,
        get_all_users_uc: GetAllUsersUseCase,
        get_users_by_role_uc: GetUsersByRoleUseCase,
        search_users_uc: SearchUsersUseCase,
        update_user_uc: UpdateUserUseCase,
        change_user_status_uc: ChangeUserStatusUseCase,
        delete_user_uc: DeleteUserUseCase
    ):
        # Inject all use cases directly
        self.create_user_uc = create_user_uc
        self.get_user_by_id_uc = get_user_by_id_uc
        self.get_user_by_email_uc = get_user_by_email_uc
        self.get_all_users_uc = get_all_users_uc
        self.get_users_by_role_uc = get_users_by_role_uc
        self.search_users_uc = search_users_uc
        self.update_user_uc = update_user_uc
        self.change_user_status_uc = change_user_status_uc
        self.delete_user_uc = delete_user_uc

    # CREATE Operations
    @BaseController.handle_exceptions
    @validate.validate_input(UserCreateSchema)
    async def create_user(
        self, 
        input_data: Dict[str, Any], 
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Create a new user account
        Uses: CreateUserUseCase
        """
        result = await self.create_user_uc.execute(input_data, None, context or {})
        return result

    # READ Operations
    @BaseController.handle_exceptions
    async def get_user_by_id(
        self, 
        user_id: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Get user by ID
        Uses: GetUserByIdUseCase
        """
        input_data = {'user_id': user_id}
        result = await self.get_user_by_id_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
    async def get_user_by_email(
        self, 
        email: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Get user by email
        Uses: GetUserByEmailUseCase
        """
        input_data = {'email': email}
        result = await self.get_user_by_email_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
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
        Uses: GetAllUsersUseCase
        """
        input_data = {
            'filters': filters or {},
            'page': page,
            'per_page': per_page
        }
        result = await self.get_all_users_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
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
        Uses: GetUsersByRoleUseCase
        """
        input_data = {
            'role': role,
            'page': page,
            'per_page': per_page
        }
        result = await self.get_users_by_role_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
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
        Uses: SearchUsersUseCase
        """
        input_data = {
            'search_term': search_term,
            'page': page,
            'per_page': per_page
        }
        result = await self.search_users_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
    async def get_current_user_profile(
        self,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Get current authenticated user's profile
        Uses: GetUserByIdUseCase internally
        """
        from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
        
        if not current_user or not hasattr(current_user, 'id'):
            raise InvalidUserInputException(
                field_errors={"user": ["User authentication required"]},
                user_message="User authentication required."
            )
        
        input_data = {'user_id': str(current_user.id)}
        result = await self.get_user_by_id_uc.execute(input_data, current_user, context or {})
        return result

    # UPDATE Operations
    @BaseController.handle_exceptions
    async def update_user(
        self,
        user_id: str,
        update_data: Dict[str, Any],
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Update user profile
        Uses: UpdateUserUseCase
        """
        input_data = {
            'user_id': user_id,
            'update_data': update_data
        }
        result = await self.update_user_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
    @validate.validate_optional(UserUpdateSchema)
    async def update_current_user_profile(
        self,
        update_data: Dict[str, Any],
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Update current authenticated user's profile
        Uses: UpdateUserUseCase internally
        """
        from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException
        
        if not current_user or not hasattr(current_user, 'id'):
            raise InvalidUserInputException(
                field_errors={"user": ["User authentication required"]},
                user_message="User authentication required."
            )
        
        input_data = {
            'user_id': str(current_user.id),
            'update_data': update_data
        }
        result = await self.update_user_uc.execute(input_data, current_user, context or {})
        return result

    @BaseController.handle_exceptions
    async def change_user_status(
        self,
        user_id: str,
        status: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Change user status
        Uses: ChangeUserStatusUseCase
        """
        input_data = {
            'user_id': user_id,
            'status': status
        }
        result = await self.change_user_status_uc.execute(input_data, current_user, context or {})
        return result

    # DELETE Operations
    @BaseController.handle_exceptions
    async def delete_user(
        self,
        user_id: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Soft delete user
        Uses: DeleteUserUseCase
        """
        input_data = {'user_id': user_id}
        result = await self.delete_user_uc.execute(input_data, current_user, context or {})
        return result

    # BATCH Operations
    @BaseController.handle_exceptions
    async def bulk_change_status(
        self,
        user_ids: List[str],
        status: str,
        current_user: Any,
        context: Dict[str, Any] = None
    ) -> APIResponse:
        """
        Bulk change user statuses
        Uses: ChangeUserStatusUseCase internally for each user
        """
        results = []
        errors = []
        
        for user_id in user_ids:
            try:
                input_data = {'user_id': user_id, 'status': status}
                result = await self.change_user_status_uc.execute(
                    input_data, current_user, context or {}
                )
                results.append({'user_id': user_id, 'success': True})
            except Exception as e:
                errors.append({'user_id': user_id, 'error': str(e)})
                logger.error(f"Failed to update status for user {user_id}: {str(e)}")
        
        return APIResponse.success_response(
            message=f"Bulk status update completed. Success: {len(results)}, Failed: {len(errors)}",
            data={
                'successful_updates': results,
                'failed_updates': errors
            }
        )


# New Factory Functions using your dependency injection
def create_user_controller_with_di() -> UserController:
    """
    Create user controller using dependency injection
    This replaces the old factory function
    """
    from apps.tcc.dependencies.user_dep import (
        get_create_user_uc,
        get_user_by_id_uc,
        get_user_by_email_uc,
        get_all_users_uc,
        get_users_by_role_uc,
        get_search_users_uc,
        get_update_user_uc,
        get_change_user_status_uc,
        get_delete_user_uc
    )
    
    return UserController(
        create_user_uc=get_create_user_uc(),
        get_user_by_id_uc=get_user_by_id_uc(),
        get_user_by_email_uc=get_user_by_email_uc(),
        get_all_users_uc=get_all_users_uc(),
        get_users_by_role_uc=get_users_by_role_uc(),
        search_users_uc=get_search_users_uc(),
        update_user_uc=get_update_user_uc(),
        change_user_status_uc=get_change_user_status_uc(),
        delete_user_uc=get_delete_user_uc()
    )


# Legacy factory function for backward compatibility
def create_user_controller(
    user_repository = None,  # Keep parameter for backward compatibility
    jwt_uc = None           # Keep parameter for backward compatibility
) -> UserController:
    """
    Legacy factory function - now uses dependency injection internally
    Maintains backward compatibility with existing code
    """
    return create_user_controller_with_di()