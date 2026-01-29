import asyncio
from datetime import datetime, timedelta
from pydantic import ValidationError
from apps.core.schemas.input_schemas.auth import LoginInputSchema
from apps.core.schemas.out_schemas.aut_out_schemas import LoginResponseSchema, TokenResponseSchema
from apps.core.schemas.out_schemas.user_out_schemas import UserSimpleResponseSchema
from apps.tcc.usecase.usecases.base.base_uc import BaseUseCase
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    InvalidAuthInputException,
    AccountInactiveException
)
from apps.tcc.usecase.domain_exception.u_exceptions import AccountLockedException
from apps.tcc.usecase.repo.domain_repo.user_repo import UserRepository
from apps.core.jwt.jwt_backend import get_jwt_backend  # Changed to use JWTBackend
from apps.tcc.usecase.usecases.base.password_service import PasswordService

import logging
logger = logging.getLogger(__name__)


class LoginUseCase(BaseUseCase):

    def __init__(self, user_repository: UserRepository, 
             password_service: PasswordService,
             auth_service=None):
        super().__init__()
        self.user_repository = user_repository
        self.password_service = password_service
        self.auth_service = auth_service
        
        # Initialize JWT backend - FIXED: Make this optional initialization
        self.jwt_backend = None
        try:
            from apps.core.jwt.jwt_backend import get_jwt_backend
            self.jwt_backend = get_jwt_backend()
            logger.info("JWTBackend initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize JWTBackend: {e}")
            
        if not self.jwt_backend:
            logger.error("JWTBackend not available - cannot generate tokens")
            raise InvalidAuthInputException(
                field_errors={"general": ["Authentication service unavailable"]},
                user_message="Unable to complete login. Please try again.",
            )

    def _setup_configuration(self):
        self.config.require_authentication = False
        self.config.transactional = False
        self.config.audit_log = True
        self.config.validate_input = True

    async def _validate_input(self, data, ctx):
        """Validate login input with clear error messages."""
        # Add logging to see what data is coming in
        logger.debug(f"Login validation data: {data}")
        
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
            logger.debug(f"Input validated successfully for email: {email}")
        except ValidationError as e:
            field_errors = {}
            for err in e.errors():
                field = err["loc"][0]
                msg = err["msg"]

                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
                
            logger.error(f"Validation error: {field_errors}")

            raise InvalidAuthInputException(
                field_errors=field_errors,
                user_message="Invalid login data.",
            )

    async def _on_execute(self, data, user, ctx):
        login_input = self.validated_input
        
        # Convert email to lowercase for consistency
        email = login_input.email.lower()
        
        logger.info(f"Login attempt for email: {email}")

        # 1. Fetch user
        user_entity = await self.user_repository.get_by_email(
            email,
            include_password_hash=True
        )

        if not user_entity:
            logger.warning(f"User not found for email: {email}")
            raise InvalidAuthInputException(
                field_errors={"credentials": ["Invalid email or password"]},
                user_message="Invalid email or password.",
            )

        logger.info(f"User found: {user_entity.id}, email: {user_entity.email}")

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
            logger.warning(f"Invalid password for user: {user_entity.email}")
            await self._track_failed_login(user_entity.id)
            raise InvalidAuthInputException(
                field_errors={"credentials": ["Invalid email or password"]},
                user_message="Invalid email or password.",  # Generic message
                operation_id=ctx.get('operation_id') if isinstance(ctx, dict) else None
            )

        await self._reset_failed_logins(user_entity.id)

        # 4. Get user role and permissions - CRITICAL FIX
        role = None
        
        # Check Django user model fields first
        if hasattr(user_entity, 'role'):
            role = getattr(user_entity, 'role')
        elif hasattr(user_entity, 'user_role'):
            role = getattr(user_entity, 'user_role')
        elif hasattr(user_entity, 'role_type'):
            role = getattr(user_entity, 'role_type')
        else:
            # Try to get from Django's built-in fields
            role = getattr(user_entity, 'groups', None)
            if role:
                # Take the first group name
                role = role.first().name if hasattr(role, 'first') and role.exists() else 'member'
            else:
                role = 'member'  # Default
        
        # Ensure role is lowercase string
        if isinstance(role, str):
            role = role.lower()
        else:
            role = str(role).lower() if role else 'member'
        
        # Get is_superuser and is_staff from Django user model
        is_superuser = getattr(user_entity, "is_superuser", False)
        is_staff = getattr(user_entity, "is_staff", False)
        
        # If not set in Django fields, determine from role
        if not is_superuser and role in ['super_admin', 'admin']:
            is_superuser = True
        if not is_staff and role in ['super_admin', 'admin', 'staff']:
            is_staff = True
        
        logger.info(f"User role: {role}, is_superuser: {is_superuser}, is_staff: {is_staff}")

        # 5. Generate tokens using JWTBackend
        try:
            # Check if jwt_backend is initialized
            if not hasattr(self, 'jwt_backend') or self.jwt_backend is None:
                logger.error("JWTBackend not initialized")
                from apps.core.jwt.jwt_backend import get_jwt_backend
                self.jwt_backend = get_jwt_backend()
            
            # Use the updated create_tokens method
            tokens = await self.jwt_backend.create_tokens(
                user_id=str(user_entity.id),  # Ensure string
                email=user_entity.email,
                role=role,
                is_superuser=is_superuser,
                is_staff=is_staff
            )
            
            logger.info(f"Tokens generated successfully: {list(tokens.keys())}")
            
            access_token = tokens["access_token"]
            refresh_token = tokens["refresh_token"]
            expires_in = tokens.get("expires_in", 900)
            
            # Handle expires_at
            expires_at_str = tokens.get("expires_at")
            if expires_at_str:
                try:
                    # Handle ISO format string
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            else:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info(f"Tokens generated successfully for user: {user_entity.email}")
            
        except Exception as e:
            logger.error(f"Failed to generate tokens: {e}", exc_info=True)
            # Fallback to simple token generation
            expires_in = 900
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Log the error but continue
            import traceback
            logger.error(f"Token generation error: {traceback.format_exc()}")
            raise InvalidAuthInputException(
                field_errors={"general": ["Authentication service error"]},
                user_message="Unable to complete login. Please try again.",
            )

        # 6. Update last login
        try:
            await self.user_repository.update(user_entity.id, {
                "last_login": datetime.utcnow(),
                "login_count": getattr(user_entity, "login_count", 0) + 1,
                "failed_login_attempts": 0
            })
        except Exception as e:
            logger.warning(f"Failed to update last login: {e}")

        # 7. Audit log (fire-and-forget)
        if self.auth_service:
            try:
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
            except Exception as e:
                logger.warning(f"Failed to create audit log: {e}")

        # 8. Prepare user response
        user_name = getattr(user_entity, 'name', '')
        if not user_name:
            first_name = getattr(user_entity, 'first_name', '')
            last_name = getattr(user_entity, 'last_name', '')
            user_name = f"{first_name} {last_name}".strip() or user_entity.email

        created_at = getattr(user_entity, 'created_at', datetime.utcnow())
        updated_at = getattr(user_entity, 'updated_at', datetime.utcnow())
        status = getattr(user_entity, 'status', 'active')

        # Create user object
        user_response = UserSimpleResponseSchema(
            id=user_entity.id,
            email=user_entity.email,
            name=user_name,
            role=role,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            is_active=getattr(user_entity, "is_active", True),
            is_superuser=is_superuser,
            is_staff=is_staff
        )

        # Create tokens object
        token_response = TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            expires_at=expires_at
        )

        # Return response
        return LoginResponseSchema(
            user=user_response,
            tokens=token_response,
            requires_2fa=False
        )

    async def _track_failed_login(self, user_id: int):
        """Track failed login attempts - make it async-safe"""
        try:
            # Use the repository to update in an async-safe way
            user = await self.user_repository.get_by_id(user_id)
            if user:
                attempts = getattr(user, "failed_login_attempts", 0)
                
                update_data = {
                    "failed_login_attempts": attempts + 1
                }
                
                # Lock account after 5 failed attempts
                if attempts + 1 >= 5:
                    update_data.update({
                        "is_locked": True,
                        "lock_reason": "Too many failed login attempts",
                        "locked_at": datetime.utcnow()
                    })
                
                # Use repository update method which should be async-safe
                await self.user_repository.update(user_id, update_data)
                
                logger.info(f"Tracked failed login for user {user_id}, attempt {attempts + 1}")
        except Exception as e:
            # Don't break the login flow if tracking fails
            logger.error(f"Failed to track failed login: {e}")

    async def _reset_failed_logins(self, user_id: int):
        """Reset failed login counter - make it async-safe"""
        try:
            # Use repository update method
            await self.user_repository.update(user_id, {
                "failed_login_attempts": 0,
                "is_locked": False,
                "lock_reason": None,
                "locked_at": None
            })
            logger.info(f"Reset failed logins for user {user_id}")
        except Exception as e:
            # Don't break the login flow if reset fails
            logger.error(f"Failed to reset failed logins: {e}")