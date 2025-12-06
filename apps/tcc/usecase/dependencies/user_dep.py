from typing import Dict, Any, Optional
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.users.user_create_uc import CreateAdminUserUseCase, CreateUserUseCase
from apps.tcc.usecase.usecases.users.user_read_uc import (CheckEmailExistsUseCase, GetUserByIdUseCase, GetUserByEmailUseCase,  GetUsersByRoleUseCase, ListUsersUseCase, SearchUsersUseCase,
SearchUsersUseCase)
from apps.tcc.usecase.usecases.users.user_register_uc import RegisterUserUseCase
from apps.tcc.usecase.usecases.users.user_update_uc import UpdateUserUseCase,ChangeUserStatusUseCase
from apps.tcc.usecase.usecases.users.user_delete_uc import DeleteUserUseCase, BulkDeleteUsersUseCase

from apps.core.cache.async_cache import AsyncCache


class UserDependencyContainer:
    """
    Clean dependency container for user use cases without JWT dependencies.
    """
    
    def __init__(self, cache: Optional[AsyncCache] = None):
        self._cache = cache
        self._user_repository = None
        self._use_cases = {}

    async def get_user_repository(self) -> UserRepository:
        """Get or create UserRepository with caching support"""
        if self._user_repository is None:
            self._user_repository = UserRepository()
        return self._user_repository

    async def get_create_user_uc(self) -> CreateUserUseCase:
        key = 'create_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = CreateUserUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_register_user_uc(self) -> RegisterUserUseCase:
        key = 'register_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = RegisterUserUseCase(user_repository=user_repo)
        return self._use_cases[key]
    
    async def get_create_admin_user_uc(self) -> CreateAdminUserUseCase:
        key = 'create_admin_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = CreateAdminUserUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_user_by_id_uc(self) -> GetUserByIdUseCase:
        key = 'get_user_by_id'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetUserByIdUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_user_by_email_uc(self) -> GetUserByEmailUseCase:
        key = 'get_user_by_email'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetUserByEmailUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_all_users_uc(self) -> ListUsersUseCase:
        key = 'get_all_users'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = ListUsersUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_users_by_role_uc(self) -> GetUsersByRoleUseCase:
        key = 'get_users_by_role'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetUsersByRoleUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_search_users_uc(self) -> SearchUsersUseCase:
        key = 'search_users'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = SearchUsersUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_check_email_uc(self) -> CheckEmailExistsUseCase:
        key = 'check_email'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = CheckEmailExistsUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_update_user_uc(self) -> UpdateUserUseCase:
        key = 'update_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = UpdateUserUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_change_user_status_uc(self) -> ChangeUserStatusUseCase:
        key = 'change_user_status'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = ChangeUserStatusUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_delete_user_uc(self) -> DeleteUserUseCase:
        key = 'delete_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = DeleteUserUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_bulk_delete_users_uc(self) -> BulkDeleteUsersUseCase:
        key = 'bulk_delete_users'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = BulkDeleteUsersUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_all_user_use_cases(self) -> Dict[str, Any]:
        return {
            'create_user': await self.get_create_user_uc(),
            'create_admin_user': await self.get_create_admin_user_uc(),
            'get_user_by_id': await self.get_user_by_id_uc(),
            'get_user_by_email': await self.get_user_by_email_uc(),
            'get_all_users': await self.get_all_users_uc(),
            'get_users_by_role': await self.get_users_by_role_uc(),
            'search_users': await self.get_search_users_uc(),
            'check_email': await self.get_check_email_uc(),
            'update_user': await self.get_update_user_uc(),
            'change_user_status': await self.get_change_user_status_uc(),
            'delete_user': await self.get_delete_user_uc(),
            'bulk_delete_users': await self.get_bulk_delete_users_uc(),
        }


# Global instance
_user_dependency_container: Optional[UserDependencyContainer] = None

async def get_user_dependency_container(cache: Optional[AsyncCache] = None) -> UserDependencyContainer:
    global _user_dependency_container
    if _user_dependency_container is None:
        _user_dependency_container = UserDependencyContainer(cache=cache)
    return _user_dependency_container
