import asyncio
from datetime import datetime, timedelta
from pydantic import ValidationError
from apps.core.schemas.input_schemas.auth import LoginInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import LoginResponseSchema, TokenResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema, UserSimpleResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    InvalidAuthInputException,
    AccountInactiveException
)
from apps.tcc.usecase.domain_exception.u_exceptions import AccountLockedException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.core.jwt.jwt_backend import JWTManager
from apps.tcc.usecase.usecases.base.password_service import PasswordService

import logging
logger = logging.getLogger(__name__)


class LoginUseCase(BaseUseCase):

    def __init__(self, user_repository: UserRepository, 
                 jwt_service: JWTManager, 
                 password_service: PasswordService,
                 auth_service=None):

        super().__init__()
        self.user_repository = user_repository
        self.jwt_service = jwt_service
        self.password_service = password_service
        self.auth_service = auth_service

    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.transactional = False
        self.config.audit_log = True
        self.config.validate_input = True

    async def _validate_input(self, data, ctx):
        """Validate login input with clear error messages."""
        if not data or not isinstance(data, dict):
            raise InvalidAuthInputException(
                field_errors={"general": ["Login data is required"]},
                user_message="Please provide email and password.",
            )

        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email:
            raise InvalidAuthInputException(
                field_errors={"email": ["Email is required"]},
                user_message="Email is required.",
            )

        if not password:
            raise InvalidAuthInputException(
                field_errors={"password": ["Password is required"]},
                user_message="Password is required.",
            )

        try:
            self.validated_input = LoginInputSchema(**data)
        except ValidationError as e:
            field_errors = {}
            for err in e.errors():
                field = err["loc"][0]
                msg = err["msg"]

                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)

            raise InvalidAuthInputException(
                field_errors=field_errors,
                user_message="Invalid login data.",
            )

    async def _on_execute(self, data, user, ctx):
        login_input = self.validated_input

        # 1. Fetch user
        user_entity = await self.user_repository.get_by_email(
            login_input.email,
            include_password_hash=True
        )

        if not user_entity:
            raise InvalidAuthInputException(
                field_errors={"credentials": ["Invalid email or password"]},
                user_message="Invalid email or password.",
            )

        # 2. Check status
        if getattr(user_entity, "is_locked", False):
            raise AccountLockedException(
                user_id=str(user_entity.id),
                lock_reason=user_entity.lock_reason,
                user_message="Your account is locked."
            )

        if not getattr(user_entity, "is_active", True):
            raise AccountInactiveException(
                username=user_entity.email,
                user_id=user_entity.id
            )

        # 3. Verify password
        password_valid = await self.password_service.verify_password(
            login_input.password,
            user_entity.password_hash
        )

        if not password_valid:
            await self._track_failed_login(user_entity.id)
            raise InvalidAuthInputException(
                field_errors={"credentials": ["Invalid email or password"]},
                user_message="Invalid email or password.",
            )

        await self._reset_failed_logins(user_entity.id)

        # 4. Prepare roles
        roles = getattr(user_entity, "roles", [])
        if not roles and hasattr(user_entity, "role"):
            roles = [user_entity.role]

        # 5. Generate tokens (ASYNC)
        access_token =  self.jwt_service.generate_access_token(
            user_id=user_entity.id,
            email=user_entity.email,
            roles=roles
        )

        refresh_token =  self.jwt_service.generate_refresh_token(
            user_id=user_entity.id,
            email=user_entity.email
        )

        # 6. Update last login
        await self.user_repository.update(user_entity.id, {
            "last_login": datetime.utcnow(),
            "login_count": getattr(user_entity, "login_count", 0) + 1,
            "failed_login_attempts": 0
        })

        # 7. Audit log (fire-and-forget)
        if self.auth_service:
            # Safely get request_meta from context
            request_meta = {}
            if hasattr(ctx, 'request_meta'):
                request_meta = ctx.request_meta
            elif isinstance(ctx, dict):
                request_meta = ctx.get("request_meta", {})
            
            asyncio.create_task(
                self.auth_service.audit_login_async(
                    user_entity.id, "LOGIN", request_meta
                )
            )

        user_name = getattr(user_entity, 'name', '')
        if not user_name:
            first_name = getattr(user_entity, 'first_name', '')
            last_name = getattr(user_entity, 'last_name', '')
            user_name = f"{first_name} {last_name}".strip() or user_entity.email

        single_role = roles[0] if roles else 'member'
        created_at = getattr(user_entity, 'created_at', datetime.utcnow())
        updated_at = getattr(user_entity, 'updated_at', datetime.utcnow())
        status = getattr(user_entity, 'status', 'active')

        # Create user object
        user = UserSimpleResponseSchema(
            id=user_entity.id,
            email=user_entity.email,
            name=user_name,
            role=single_role,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            is_active=getattr(user_entity, "is_active", True)
        )

        # Create tokens object
        tokens = TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,
            expires_at=datetime.utcnow() + timedelta(seconds=900)
        )

        # Return response
        return LoginResponseSchema(
            user=user,
            tokens=tokens,
            requires_2fa=False
        )
            
            
    async def _track_failed_login(self, user_id: int):
        user = await self.user_repository.get_by_id(user_id)
        attempts = getattr(user, "failed_login_attempts", 0)

        if attempts + 1 >= 5:
            await self.user_repository.update(user_id, {
                "is_locked": True,
                "lock_reason": "Too many failed attempts",
                "failed_login_attempts": attempts + 1
            })
        else:
            await self.user_repository.update(user_id, {
                "failed_login_attempts": attempts + 1
            })

    async def _reset_failed_logins(self, user_id: int):
        await self.user_repository.update(user_id, {
            "failed_login_attempts": 0,
            "is_locked": False,
            "lock_reason": None
        })
