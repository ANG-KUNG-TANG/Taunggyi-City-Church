from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.auth.change_password import ChangePasswordUseCase
from apps.tcc.usecase.usecases.auth.forgot_password import ForgotPasswordUseCase
from apps.tcc.usecase.usecases.auth.login_uc import LoginUseCase
from apps.tcc.usecase.usecases.auth.logout_uc import LogoutUseCase
from apps.tcc.usecase.usecases.auth.refresh_uc import RefreshTokenUseCase
from apps.tcc.usecase.usecases.auth.reset_password import ResetPasswordUseCase
from apps.tcc.usecase.usecases.auth.verify_uc import VerifyTokenUseCase
from apps.tcc.usecase.usecases.base.password_service import PasswordService
from apps.core.jwt.jwt_backend import JWTManager

# Lazy-loaded singletons
_user_repository = None
_auth_service = None
_jwt_service = None
_password_service = None

async def get_user_repository() -> UserRepository:
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository

async def get_auth_service() -> AsyncAuthDomainService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AsyncAuthDomainService()
    return _auth_service

async def get_jwt_service() -> JWTManager:
    global _jwt_service
    if _jwt_service is None:
        from apps.core.jwt.jwt_backend import JWTBackend
        backend = JWTBackend.get_instance()
        _jwt_service = backend.jwt_manager
    return _jwt_service

# async def get_change_password_uc() -> ChangePasswordUseCase:
#     """Dependency: ChangePasswordUseCase instance"""
#     cache_key = 'change_password_uc'
#     if cache_key not in _instance_cache:
#         user_repo = await get_user_repository()
#         password_service = await get_password_service()
#         auth_service = await get_auth_service()
        
#         _instance_cache[cache_key] = ChangePasswordUseCase(
#             user_repository=user_repo,
#             password_service=password_service,
#             auth_service=auth_service
#         )
#     return _instance_cache[cache_key]

async def get_password_service() -> PasswordService:
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service

# Use case factories (create new instances each time)
async def get_login_uc() -> LoginUseCase:
    return LoginUseCase(
        user_repository=await get_user_repository(),
        jwt_service=await get_jwt_service(),
        password_service=await get_password_service(),
        auth_service=await get_auth_service()
    )

async def get_logout_uc() -> LogoutUseCase:
    return LogoutUseCase(
        auth_service=await get_auth_service(),
        jwt_service=await get_jwt_service()
    )

async def get_refresh_uc() -> RefreshTokenUseCase:
    return RefreshTokenUseCase(
        user_repository=await get_user_repository(),
        jwt_service=await get_jwt_service()
    )

async def get_forgot_password_uc() -> ForgotPasswordUseCase:
    return ForgotPasswordUseCase(
        user_repository=await get_user_repository(),
        auth_service=await get_auth_service()
    )

async def get_reset_password_uc() -> ResetPasswordUseCase:
    return ResetPasswordUseCase(
        user_repository=await get_user_repository(),
        auth_service=await get_auth_service(),
        password_service=await get_password_service()
    )

async def get_verify_token_uc() -> VerifyTokenUseCase:
    return VerifyTokenUseCase(
        user_repository=await get_user_repository()
    )