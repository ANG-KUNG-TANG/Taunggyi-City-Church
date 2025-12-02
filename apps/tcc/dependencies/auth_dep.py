from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.tcc.usecase.services.auth.auth_service import AsyncAuthDomainService
from apps.tcc.usecase.usecases.auth.forgot_passowrd import ForgotPasswordUseCase
from apps.tcc.usecase.usecases.auth.login_uc import LoginUseCase
from apps.tcc.usecase.usecases.auth.logout_uc import LogoutUseCase
from apps.tcc.usecase.usecases.auth.refresh_uc import RefreshTokenUseCase
from apps.tcc.usecase.usecases.auth.reset_password import ResetPasswordUseCase
from apps.tcc.usecase.usecases.auth.verify_uc import VerifyTokenUseCase
from apps.tcc.usecase.usecases.users.user_create_uc import CreateUserUseCase

# Mock email service for development
class MockEmailService:
    """Mock email service for development"""
    
    async def send_password_reset_email(self, email: str, reset_link: str, **kwargs) -> bool:
        print(f"[DEV] Password reset email would be sent to: {email}")
        print(f"[DEV] Reset link: {reset_link}")
        print(f"[DEV] Additional context: {kwargs}")
        return True
    
    async def send_password_changed_notification(self, email: str, **kwargs) -> bool:
        print(f"[DEV] Password changed notification would be sent to: {email}")
        print(f"[DEV] Additional context: {kwargs}")
        return True
    
    async def send_email_verification(self, email: str, verification_link: str, **kwargs) -> bool:
        print(f"[DEV] Email verification would be sent to: {email}")
        print(f"[DEV] Verification link: {verification_link}")
        return True

# ============ REPOSITORIES ============

async def get_user_repository() -> UserRepository:
    """Dependency: UserRepository instance"""
    return UserRepository()

# ============ SERVICES ============

async def get_auth_service() -> AsyncAuthDomainService:
    """Dependency: AsyncAuthDomainService instance"""
    return AsyncAuthDomainService()

async def get_email_service():
    """Dependency: Email service (mock for development)"""
    return MockEmailService()

async def get_jwt_provider():
    """Dependency: JWT provider with configurable RSA keys"""
    from apps.core.jwt.jwt_backend import JWTManager, TokenConfig, JWTBackend
    from django.conf import settings
    
    jwt_config = settings.JWT_CONFIG
    
    # Create TokenConfig from settings
    config = TokenConfig(
        access_token_expiry=jwt_config['ACCESS_TOKEN_EXPIRY'],
        refresh_token_expiry=jwt_config['REFRESH_TOKEN_EXPIRY'],
        reset_token_expiry=jwt_config['RESET_TOKEN_EXPIRY'],
        algorithm=jwt_config['ALGORITHM'],
        issuer=jwt_config['ISSUER'],
        audience=jwt_config['AUDIENCE']
    )
    
    # Check if RSA keys are provided in settings
    private_key = getattr(settings, 'JWT_PRIVATE_KEY', None)
    public_key = getattr(settings, 'JWT_PUBLIC_KEY', None)
    
    if private_key and public_key and jwt_config['ALGORITHM'].startswith('RS'):
        # Production: Use provided RSA keys
        print("✅ PRODUCTION: Using configured RSA keys")
        return JWTManager(
            config=config,
            private_key=private_key,
            public_key=public_key
        )
    elif getattr(settings, 'JWT_AUTO_GENERATE_KEYS', False):
        # Development: Auto-generate RSA keys
        print("⚠️ DEVELOPMENT: Auto-generating RSA keys")
        backend = JWTBackend.get_instance()
        await backend.initialize()
        return backend.jwt_manager
    else:
        # Fallback: HMAC (not for production)
        print("⚠️ FALLBACK: Using HMAC - NOT FOR PRODUCTION")
        config = TokenConfig(
            access_token_expiry=jwt_config['ACCESS_TOKEN_EXPIRY'],
            refresh_token_expiry=jwt_config['REFRESH_TOKEN_EXPIRY'],
            reset_token_expiry=jwt_config['RESET_TOKEN_EXPIRY'],
            algorithm='HS256',
            issuer=jwt_config['ISSUER'],
            audience=jwt_config['AUDIENCE']
        )
        secret_key = getattr(settings, 'JWT_SECRET_KEY', 'change-this-in-production')
        return JWTManager(
            config=config,
            private_key=secret_key,
            public_key=secret_key
        )

# ============ USE CASES ============

async def get_login_uc() -> LoginUseCase:
    """Dependency: LoginUseCase instance"""
    jwt_provider = await get_jwt_provider()
    auth_service = await get_auth_service()
    return LoginUseCase(jwt_provider=jwt_provider, auth_service=auth_service)

async def get_logout_uc() -> LogoutUseCase:
    """Dependency: LogoutUseCase instance"""
    auth_service = await get_auth_service()
    return LogoutUseCase(auth_service=auth_service)

async def get_refresh_uc() -> RefreshTokenUseCase:
    """Dependency: RefreshTokenUseCase instance"""
    user_repository = await get_user_repository()
    jwt_provider = await get_jwt_provider()
    return RefreshTokenUseCase(user_repository=user_repository, jwt_provider=jwt_provider)

async def get_verify_uc() -> VerifyTokenUseCase:
    """Dependency: VerifyTokenUseCase instance"""
    return VerifyTokenUseCase()

async def get_register_uc() -> CreateUserUseCase:
    """Dependency: CreateUserUseCase instance (from user module)"""
    from apps.tcc.dependencies.user_dep import get_create_user_use_case
    return await get_create_user_use_case()

async def get_forgot_password_uc() -> ForgotPasswordUseCase:
    """Dependency: ForgotPasswordUseCase instance"""
    user_repository = await get_user_repository()
    auth_service = await get_auth_service()
    email_service = await get_email_service()
    
    return ForgotPasswordUseCase(
        user_repository=user_repository,
        auth_service=auth_service,
        email_service=email_service
    )

async def get_reset_password_uc() -> ResetPasswordUseCase:
    """Dependency: ResetPasswordUseCase instance"""
    user_repository = await get_user_repository()
    auth_service = await get_auth_service()
    return ResetPasswordUseCase(
        user_repository=user_repository,
        auth_service=auth_service
    )