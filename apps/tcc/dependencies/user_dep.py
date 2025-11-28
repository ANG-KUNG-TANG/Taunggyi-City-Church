from typing import Dict, Any
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.users.user_create_uc import CreateUserUseCase
from apps.tcc.usecase.usecases.users.user_read_uc import (
    GetUserByIdUseCase, GetUserByEmailUseCase, GetAllUsersUseCase,
    GetUsersByRoleUseCase, SearchUsersUseCase
)
from apps.tcc.usecase.usecases.users.user_update_uc import UpdateUserUseCase, ChangeUserStatusUseCase
from apps.tcc.usecase.usecases.users.user_delete_uc import DeleteUserUseCase
from apps.tcc.usecase.usecases.auth.jwt_uc import JWTCreateUseCase

# Repository
async def get_user_repository() -> UserRepository:
    return UserRepository()

# Auth
async def get_jwt_uc() -> JWTCreateUseCase:
    return JWTCreateUseCase()

# Use Cases
async def get_create_user_uc() -> CreateUserUseCase:
    user_repo = await get_user_repository()
    jwt_uc = await get_jwt_uc()
    return CreateUserUseCase(user_repository=user_repo, jwt_uc=jwt_uc)

async def get_user_by_id_uc() -> GetUserByIdUseCase:
    user_repo = await get_user_repository()
    return GetUserByIdUseCase(user_repository=user_repo)

async def get_user_by_email_uc() -> GetUserByEmailUseCase:
    user_repo = await get_user_repository()
    return GetUserByEmailUseCase(user_repository=user_repo)

async def get_all_users_uc() -> GetAllUsersUseCase:
    user_repo = await get_user_repository()
    return GetAllUsersUseCase(user_repository=user_repo)

async def get_users_by_role_uc() -> GetUsersByRoleUseCase:
    user_repo = await get_user_repository()
    return GetUsersByRoleUseCase(user_repository=user_repo)

async def get_search_users_uc() -> SearchUsersUseCase:
    user_repo = await get_user_repository()
    return SearchUsersUseCase(user_repository=user_repo)

async def get_update_user_uc() -> UpdateUserUseCase:
    user_repo = await get_user_repository()
    return UpdateUserUseCase(user_repository=user_repo)

async def get_change_user_status_uc() -> ChangeUserStatusUseCase:
    user_repo = await get_user_repository()
    return ChangeUserStatusUseCase(user_repository=user_repo)

async def get_delete_user_uc() -> DeleteUserUseCase:
    user_repo = await get_user_repository()
    return DeleteUserUseCase(user_repository=user_repo)