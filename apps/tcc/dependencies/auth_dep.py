from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.auth.login_uc import LoginUseCase
from apps.tcc.usecase.usecases.auth.logout_uc import LogoutUseCase
from apps.tcc.usecase.usecases.auth.refresh_uc import RefreshTokenUseCase
from apps.tcc.usecase.usecases.auth.verify_uc import VerifyTokenUseCase
from apps.tcc.usecase.usecases.users.user_create_uc import CreateUserUseCase

# Repository
async def get_user_repository() -> UserRepository:
    return UserRepository()

# Services
async def get_auth_service() -> AsyncAuthDomainService:
    return AsyncAuthDomainService()

async def get_jwt_provider():
    # This should return your JWT provider instance
    from apps.core.security.jwt_manager import JWTManager
    return JWTManager()

# Use Cases
async def get_login_uc() -> LoginUseCase:
    jwt_provider = await get_jwt_provider()
    auth_service = await get_auth_service()
    return LoginUseCase(jwt_provider=jwt_provider, auth_service=auth_service)

async def get_logout_uc() -> LogoutUseCase:
    auth_service = await get_auth_service()
    return LogoutUseCase(auth_service=auth_service)

async def get_refresh_uc() -> RefreshTokenUseCase:
    user_repository = await get_user_repository()
    jwt_provider = await get_jwt_provider()
    return RefreshTokenUseCase(user_repository=user_repository, jwt_provider=jwt_provider)

async def get_verify_uc() -> VerifyTokenUseCase:
    return VerifyTokenUseCase()

async def get_register_uc() -> CreateUserUseCase:
    # Reuse the existing CreateUserUseCase for registration
    from apps.tcc.dependencies.user_dep import get_create_user_uc
    return await get_create_user_uc()