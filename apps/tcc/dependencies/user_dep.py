from functools import lru_cache
from typing import AsyncGenerator

# 1. Import Repositories
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository

# 2. Import Shared/Base Use Cases
from apps.tcc.usecase.usecases.base.jwt_uc import JWTCreateUseCase

# 3. Import User Domain Use Cases
from apps.tcc.usecase.usecases.users.user_create_uc import CreateUserUseCase
from apps.tcc.usecase.usecases.users.user_read_uc import (
    GetUserByIdUseCase,
    GetUserByEmailUseCase,
    GetAllUsersUseCase,
    GetUsersByRoleUseCase,
    SearchUsersUseCase
)
from apps.tcc.usecase.usecases.users.user_update_uc import (
    UpdateUserUseCase,
    ChangeUserStatusUseCase
)
from apps.tcc.usecase.usecases.users.user_delete_uc import DeleteUserUseCase

# --- Repository Providers ---

@lru_cache()
def get_user_repository() -> UserRepository:
    """
    Creates a singleton instance of the User Repository.
    """
    return UserRepository()

# --- Shared Logic Providers ---

def get_jwt_create_uc() -> JWTCreateUseCase:
    """
    Provides the JWT creation use case required by CreateUserUseCase.
    """
    # Assuming JWTCreateUseCase might need its own dependencies or config
    return JWTCreateUseCase()

# --- User Use Case Factories ---

def get_create_user_uc() -> CreateUserUseCase:
    """Dependency provider for CreateUserUseCase"""
    return CreateUserUseCase(
        user_repository=get_user_repository(),
        jwt_uc=get_jwt_create_uc()
    )

def get_user_by_id_uc() -> GetUserByIdUseCase:
    """Dependency provider for GetUserByIdUseCase"""
    return GetUserByIdUseCase(
        user_repository=get_user_repository()
    )

def get_user_by_email_uc() -> GetUserByEmailUseCase:
    """Dependency provider for GetUserByEmailUseCase"""
    return GetUserByEmailUseCase(
        user_repository=get_user_repository()
    )

def get_all_users_uc() -> GetAllUsersUseCase:
    """Dependency provider for GetAllUsersUseCase"""
    return GetAllUsersUseCase(
        user_repository=get_user_repository()
    )

def get_users_by_role_uc() -> GetUsersByRoleUseCase:
    """Dependency provider for GetUsersByRoleUseCase"""
    return GetUsersByRoleUseCase(
        user_repository=get_user_repository()
    )

def get_search_users_uc() -> SearchUsersUseCase:
    """Dependency provider for SearchUsersUseCase"""
    return SearchUsersUseCase(
        user_repository=get_user_repository()
    )

def get_update_user_uc() -> UpdateUserUseCase:
    """Dependency provider for UpdateUserUseCase"""
    return UpdateUserUseCase(
        user_repository=get_user_repository()
    )

def get_change_user_status_uc() -> ChangeUserStatusUseCase:
    """Dependency provider for ChangeUserStatusUseCase"""
    return ChangeUserStatusUseCase(
        user_repository=get_user_repository()
    )

def get_delete_user_uc() -> DeleteUserUseCase:
    """Dependency provider for DeleteUserUseCase"""
    return DeleteUserUseCase(
        user_repository=get_user_repository()
    )