from typing import Dict, Any, Optional
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.users.user_create_uc import CreateUserUseCase
from apps.tcc.usecase.usecases.users.user_read_uc import (
    GetUserByIdUseCase, GetUserByEmailUseCase, GetAllUsersUseCase,
    GetUsersByRoleUseCase, SearchUsersUseCase
)
from apps.tcc.usecase.usecases.users.user_update_uc import (
    UpdateUserUseCase, ChangeUserStatusUseCase, VerifyPasswordUseCase
)
from apps.tcc.usecase.usecases.users.user_delete_uc import DeleteUserUseCase
from apps.tcc.usecase.usecases.auth.jwt_uc import JWTCreateUseCase
from apps.core.cache.async_cache import AsyncCache
from apps.core.jwt.jwt_backend import JWTManager


class UserDependencyContainer:
    """
    Dependency container for user use cases.
    Manages creation and dependency injection for all user-related use cases.
    """
    
    def __init__(self, cache: Optional[AsyncCache] = None, jwt_manager: Optional[JWTManager] = None):
        self._cache = cache
        self._jwt_manager = jwt_manager
        self._user_repository = None
        self._jwt_uc = None
        
        # Use case instances cache
        self._use_cases = {}

    # Repository
    async def get_user_repository(self) -> UserRepository:
        """Get or create UserRepository with caching support"""
        if self._user_repository is None:
            self._user_repository = UserRepository(cache=self._cache)
        return self._user_repository

    # JWT Dependencies - FIXED
    async def get_jwt_manager(self) -> JWTManager:
        """Get or create JWTManager"""
        if self._jwt_manager is None:
            # Import the existing jwt provider from auth_dep.py
            from apps.tcc.dependencies.auth_dep import get_jwt_provider
            self._jwt_manager = await get_jwt_provider()
        return self._jwt_manager

    async def get_jwt_uc(self) -> JWTCreateUseCase:
        """Get or create JWTCreateUseCase"""
        if self._jwt_uc is None:
            jwt_manager = await self.get_jwt_manager()
            self._jwt_uc = JWTCreateUseCase(jwt_manager=jwt_manager)
        return self._jwt_uc

    # Use Case Factories
    async def get_create_user_uc(self) -> CreateUserUseCase:
        """Get CreateUserUseCase with dependencies"""
        key = 'create_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            jwt_uc = await self.get_jwt_uc()
            self._use_cases[key] = CreateUserUseCase(
                user_repository=user_repo, 
                jwt_uc=jwt_uc
            )
        return self._use_cases[key]

    async def get_user_by_id_uc(self) -> GetUserByIdUseCase:
        """Get GetUserByIdUseCase"""
        key = 'get_user_by_id'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetUserByIdUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_user_by_email_uc(self) -> GetUserByEmailUseCase:
        """Get GetUserByEmailUseCase"""
        key = 'get_user_by_email'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetUserByEmailUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_all_users_uc(self) -> GetAllUsersUseCase:
        """Get GetAllUsersUseCase"""
        key = 'get_all_users'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetAllUsersUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_users_by_role_uc(self) -> GetUsersByRoleUseCase:
        """Get GetUsersByRoleUseCase"""
        key = 'get_users_by_role'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = GetUsersByRoleUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_search_users_uc(self) -> SearchUsersUseCase:
        """Get SearchUsersUseCase"""
        key = 'search_users'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = SearchUsersUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_update_user_uc(self) -> UpdateUserUseCase:
        """Get UpdateUserUseCase"""
        key = 'update_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = UpdateUserUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_change_user_status_uc(self) -> ChangeUserStatusUseCase:
        """Get ChangeUserStatusUseCase"""
        key = 'change_user_status'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = ChangeUserStatusUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_verify_password_uc(self) -> VerifyPasswordUseCase:
        """Get VerifyPasswordUseCase"""
        key = 'verify_password'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = VerifyPasswordUseCase(user_repository=user_repo)
        return self._use_cases[key]

    async def get_delete_user_uc(self) -> DeleteUserUseCase:
        """Get DeleteUserUseCase"""
        key = 'delete_user'
        if key not in self._use_cases:
            user_repo = await self.get_user_repository()
            self._use_cases[key] = DeleteUserUseCase(user_repository=user_repo)
        return self._use_cases[key]

    # Bulk operations
    async def get_all_user_use_cases(self) -> Dict[str, Any]:
        """Get all user use cases at once"""
        return {
            'create_user': await self.get_create_user_uc(),
            'get_user_by_id': await self.get_user_by_id_uc(),
            'get_user_by_email': await self.get_user_by_email_uc(),
            'get_all_users': await self.get_all_users_uc(),
            'get_users_by_role': await self.get_users_by_role_uc(),
            'search_users': await self.get_search_users_uc(),
            'update_user': await self.get_update_user_uc(),
            'change_user_status': await self.get_change_user_status_uc(),
            'verify_password': await self.get_verify_password_uc(),
            'delete_user': await self.get_delete_user_uc(),
        }

    def clear_cache(self):
        """Clear all cached instances (useful for testing)"""
        self._use_cases.clear()
        self._user_repository = None
        self._jwt_uc = None


# Global instance for easy access
_user_dependency_container: Optional[UserDependencyContainer] = None

async def get_user_dependency_container(
    cache: Optional[AsyncCache] = None, 
    jwt_manager: Optional[JWTManager] = None
) -> UserDependencyContainer:
    """Get global user dependency container"""
    global _user_dependency_container
    if _user_dependency_container is None:
        _user_dependency_container = UserDependencyContainer(
            cache=cache, 
            jwt_manager=jwt_manager
        )
    return _user_dependency_container


# Individual use case getters for backward compatibility
async def get_create_user_use_case() -> CreateUserUseCase:
    container = await get_user_dependency_container()
    return await container.get_create_user_uc()

async def get_user_by_id_use_case() -> GetUserByIdUseCase:
    container = await get_user_dependency_container()
    return await container.get_user_by_id_uc()

async def get_user_by_email_use_case() -> GetUserByEmailUseCase:
    container = await get_user_dependency_container()
    return await container.get_user_by_email_uc()

async def get_all_users_use_case() -> GetAllUsersUseCase:
    container = await get_user_dependency_container()
    return await container.get_all_users_uc()

async def get_users_by_role_use_case() -> GetUsersByRoleUseCase:
    container = await get_user_dependency_container()
    return await container.get_users_by_role_uc()

async def get_search_users_use_case() -> SearchUsersUseCase:
    container = await get_user_dependency_container()
    return await container.get_search_users_uc()

async def get_update_user_use_case() -> UpdateUserUseCase:
    container = await get_user_dependency_container()
    return await container.get_update_user_uc()

async def get_change_user_status_use_case() -> ChangeUserStatusUseCase:
    container = await get_user_dependency_container()
    return await container.get_change_user_status_uc()

async def get_verify_password_use_case() -> VerifyPasswordUseCase:
    container = await get_user_dependency_container()
    return await container.get_verify_password_uc()

async def get_delete_user_use_case() -> DeleteUserUseCase:
    container = await get_user_dependency_container()
    return await container.get_delete_user_uc()