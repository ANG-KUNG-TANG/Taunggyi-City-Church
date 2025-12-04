from .user_create_uc import CreateUserUseCase, CreateAdminUserUseCase
from .user_read_uc import GetUserByEmailUseCase,GetUserByIdUseCase,ListUsersUseCase,SearchUsersUseCase,CheckEmailExistsUseCase
from .user_update_uc import UpdateUserUseCase, ChangeUserStatusUseCase
from .user_delete_uc import DeleteResponseSchema, BulkDeleteUsersUseCase

__all__ = [
    'CreateUserUseCase',
    'CreateAdminUserUseCase',
    'GetUserByIdUseCase',
    'GetUserByEmailUseCase',
    'ListUsersUseCase',
    'SearchUsersUseCase',
    'CheckEmailExistsUseCase',
    'UpdateUserUseCase',
    'ChangeUserStatusUseCase',
    'DeleteUserUseCase',
    'BulkDeleteUsersUseCase',
]

# """
# Base class for all user use cases with common functionality
# """
# from typing import Dict, Any, Optional
# from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
# from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
# import logging

# logger = logging.getLogger(__name__)

# class BaseUserUseCase(BaseUseCase):
#     """Base class for all user-related use cases"""
    
#     def __init__(self, **dependencies):
#         super().__init__(**dependencies)
#         self._ensure_user_repository()
    
#     def _ensure_user_repository(self):
#         """Ensure user_repository is available"""
#         if not hasattr(self, 'user_repository') or not self.user_repository:
#             self.user_repository = UserRepository()
#             logger.debug(f"Initialized default UserRepository for {self.__class__.__name__}")
    
#     async def _can_view_user(self, current_user, target_user_id: int) -> bool:
#         """Default implementation - override in child classes if needed"""
#         if not current_user:
#             return False
#         return current_user.id == target_user_id
    
#     async def _can_update_user(self, current_user, target_user_id: int) -> bool:
#         """Default implementation - override in child classes if needed"""
#         if not current_user:
#             return False
#         return current_user.id == target_user_id
    
#     def _validate_user_id(self, user_id) -> int:
#         """Validate and convert user_id to integer"""
#         if not user_id:
#             raise ValueError("User ID is required")
#         try:
#             return int(user_id)
#         except (ValueError, TypeError):
#             raise ValueError(f"Invalid User ID: {user_id}")
