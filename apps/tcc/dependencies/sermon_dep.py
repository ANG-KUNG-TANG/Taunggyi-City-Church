from functools import lru_cache
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.usecases.auth.jwt_uc import JWTCreateUseCase

# Import all user use cases
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

# Repository Dependencies
@lru_cache()
def get_user_repository() -> UserRepository:
    """Singleton user repository instance"""
    return UserRepository()

@lru_cache()
def get_jwt_use_case() -> JWTCreateUseCase:
    """Singleton JWT use case instance"""
    return JWTCreateUseCase()

# Create Use Cases
def get_create_user_uc() -> CreateUserUseCase:
    """Create user use case with JWT dependency"""
    return CreateUserUseCase(
        user_repository=get_user_repository(),
        jwt_uc=get_jwt_use_case()
    )

# Read Use Cases
def get_user_by_id_uc() -> GetUserByIdUseCase:
    """Get user by ID use case"""
    return GetUserByIdUseCase(get_user_repository())

def get_user_by_email_uc() -> GetUserByEmailUseCase:
    """Get user by email use case"""
    return GetUserByEmailUseCase(get_user_repository())

def get_all_users_uc() -> GetAllUsersUseCase:
    """Get all users use case"""
    return GetAllUsersUseCase(get_user_repository())

def get_users_by_role_uc() -> GetUsersByRoleUseCase:
    """Get users by role use case"""
    return GetUsersByRoleUseCase(get_user_repository())

def search_users_uc() -> SearchUsersUseCase:
    """Search users use case"""
    return SearchUsersUseCase(get_user_repository())

# Update Use Cases
def get_update_user_uc() -> UpdateUserUseCase:
    """Update user use case"""
    return UpdateUserUseCase(get_user_repository())

def get_change_user_status_uc() -> ChangeUserStatusUseCase:
    """Change user status use case"""
    return ChangeUserStatusUseCase(get_user_repository())

# Delete Use Cases
def get_delete_user_uc() -> DeleteUserUseCase:
    """Delete user use case"""
    return DeleteUserUseCase(get_user_repository())