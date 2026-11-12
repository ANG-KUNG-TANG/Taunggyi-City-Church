import asyncio
import logging
import secrets
import threading
import uuid

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from enum import Enum
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import jwt as pyjwt

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone


logger = logging.getLogger(__name__)


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    EMAIL_VERIFICATION = "email_verification"


class TokenConfig:
    """Validated JWT configuration."""

    def __init__(self):
        jwt_config = getattr(settings, "JWT_CONFIG", {})

        self.secret_key = jwt_config.get("SECRET_KEY")
        self.algorithm = str(jwt_config.get("ALGORITHM", "HS256")).upper()

        self.issuer = jwt_config.get("ISSUER")
        self.audience = jwt_config.get("AUDIENCE", ["tcc-api"])

        self.access_token_expiry = jwt_config.get("ACCESS_TOKEN_EXPIRY", 900)
        self.refresh_token_expiry = jwt_config.get("REFRESH_TOKEN_EXPIRY", 604800)
        self.reset_token_expiry = jwt_config.get("RESET_TOKEN_EXPIRY", 1800)

        private_key = jwt_config.get("PRIVATE_KEY")
        public_key = jwt_config.get("PUBLIC_KEY")

        if not isinstance(self.secret_key, str) or not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be configured.")

        if self.algorithm != "HS256":
            raise ValueError("Only HS256 is currently supported.")

        if private_key is not None or public_key is not None:
            raise ValueError("RSA keys are not supported by the HS256 implementation.")

        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ValueError("JWT issuer must be configured.")

        if isinstance(self.audience, str):
            self.audience = [self.audience]

        if (
            not isinstance(self.audience, (list, tuple))
            or not self.audience
            or any(
                not isinstance(item, str) or not item.strip() for item in self.audience
            )
        ):
            raise ValueError("JWT audience must contain at least one valid string.")

        for name, value in {
            "ACCESS_TOKEN_EXPIRY": self.access_token_expiry,
            "REFRESH_TOKEN_EXPIRY": self.refresh_token_expiry,
            "RESET_TOKEN_EXPIRY": self.reset_token_expiry,
        }.items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")

        self.audience = list(self.audience)
        self.private_key = None
        self.public_key = None

        logger.info(
            "JWT configuration initialized: algorithm=%s, issuer=%s",
            self.algorithm,
            self.issuer,
        )


class JWTManager:
    """Core synchronous JWT operations with asynchronous wrappers."""

    def __init__(self, config: TokenConfig):
        self.config = config
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    def _get_signing_key(self) -> str:
        return self.config.secret_key

    def _get_verification_key(self) -> str:
        return self.config.secret_key

    @staticmethod
    def _normalize_uuid(value: str, field_name: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            raise ValueError(f"Invalid {field_name}.") from None

    def _encode_token(
        self,
        user_id: str,
        session_id: str,
        token_type: TokenType,
        expiry_seconds: int,
    ) -> Tuple[str, Dict[str, Any]]:
        now = timezone.now()
        expires_at = now + timedelta(seconds=expiry_seconds)

        user_uuid = self._normalize_uuid(user_id, "user ID")
        session_uuid = self._normalize_uuid(
            session_id,
            "session ID",
        )

        payload = {
            "token_type": token_type.value,
            "sub": str(user_uuid),
            "session_id": str(session_uuid),
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }

        token = pyjwt.encode(
            payload,
            self._get_signing_key(),
            algorithm=self.config.algorithm,
        )

        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token, payload

    def generate_access_token(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        """Generate an access token without storing it."""

        token, _ = self._encode_token(
            user_id=user_id,
            session_id=session_id,
            token_type=TokenType.ACCESS,
            expiry_seconds=self.config.access_token_expiry,
        )

        return token

    async def generate_access_token_async(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.thread_pool,
            partial(
                self.generate_access_token,
                user_id=user_id,
                session_id=session_id,
            ),
        )

    def generate_refresh_token(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        """
        Generate a refresh token and persist only its metadata.

        The raw JWT is never stored in the database.
        """

        from apps.tcc.models.refresh_token import RefreshToken

        token, payload = self._encode_token(
            user_id=user_id,
            session_id=session_id,
            token_type=TokenType.REFRESH,
            expiry_seconds=self.config.refresh_token_expiry,
        )

        expires_at = timezone.datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.get_current_timezone(),
        )

        RefreshToken.objects.create(
            jti=payload["jti"],
            user_id=payload["sub"],
            session_id=payload["session_id"],
            expires_at=expires_at,
        )

        logger.info("Refresh token metadata persisted.")
        return token

    def verify_token_sync(
        self,
        token: str,
        token_type: TokenType = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify the JWT signature, registered claims and token type."""

        if not isinstance(token_type, TokenType):
            logger.warning("Token verification requires a valid TokenType.")
            return False, None

        if not isinstance(token, str) or not token:
            return False, None

        try:
            decoded = pyjwt.decode(
                token,
                self._get_verification_key(),
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer,
                audience=self.config.audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": [
                        "exp",
                        "iat",
                        "sub",
                        "token_type",
                        "session_id",
                        "jti",
                    ],
                },
                leeway=10,
            )

            if decoded.get("token_type") != token_type.value:
                logger.warning("JWT token type mismatch.")
                return False, None

            if not isinstance(decoded.get("sub"), str):
                return False, None

            if not isinstance(decoded.get("session_id"), str):
                return False, None

            if not isinstance(decoded.get("jti"), str):
                return False, None

            if not decoded["jti"].strip():
                return False, None

            self._normalize_uuid(decoded["sub"], "subject")
            self._normalize_uuid(
                decoded["session_id"],
                "session ID",
            )

            logger.debug(
                "JWT verified successfully: type=%s",
                token_type.value,
            )

            return True, decoded

        except pyjwt.ExpiredSignatureError:
            logger.warning("JWT verification failed: expired.")
        except pyjwt.InvalidTokenError:
            logger.warning("JWT verification failed: invalid token.")
        except ValueError:
            logger.warning("JWT verification failed: invalid UUID.")
        except Exception:
            logger.exception("Unexpected JWT verification error.")

        return False, None

    async def verify_token(
        self,
        token: str,
        token_type: TokenType = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.thread_pool,
            partial(
                self.verify_token_sync,
                token=token,
                token_type=token_type,
            ),
        )

    async def verify_refresh_token(
        self,
        token: str,
    ) -> Optional[Dict[str, Any]]:
        is_valid, payload = await self.verify_token(
            token,
            TokenType.REFRESH,
        )

        return payload if is_valid else None

    def is_token_blacklisted_sync(
        self,
        user_id: str,
        token_id: str,
    ) -> bool:
        """
        Return True when the refresh token cannot be used.

        Missing records, expired tokens, revoked tokens and consumed
        tokens are all treated as invalid.
        """

        from apps.tcc.models.refresh_token import RefreshToken

        try:
            user_uuid = self._normalize_uuid(user_id, "user ID")

            return not RefreshToken.objects.filter(
                user_id=user_uuid,
                jti=token_id,
                expires_at__gt=timezone.now(),
                revoked_at__isnull=True,
                consumed_at__isnull=True,
            ).exists()

        except (ValueError, TypeError):
            return True
        except Exception:
            logger.exception("Failed to check refresh-token state.")
            return True

    async def is_token_blacklisted(
        self,
        user_id: str,
        token_id: str,
    ) -> bool:
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.thread_pool,
            partial(
                self.is_token_blacklisted_sync,
                user_id=user_id,
                token_id=token_id,
            ),
        )

    def revoke_refresh_token_sync(
        self,
        user_id: str,
        jti: str,
    ) -> bool:
        """Revoke one unused refresh token."""

        from apps.tcc.models.refresh_token import RefreshToken

        try:
            user_uuid = self._normalize_uuid(user_id, "user ID")

            updated = RefreshToken.objects.filter(
                user_id=user_uuid,
                jti=jti,
                revoked_at__isnull=True,
                consumed_at__isnull=True,
            ).update(
                revoked_at=timezone.now(),
            )

            return updated > 0

        except (ValueError, TypeError):
            return False
        except Exception:
            logger.exception("Failed to revoke refresh token.")
            return False


class JWTBackend:
    """Application-facing JWT service."""

    _instance: Optional["JWTBackend"] = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        config: TokenConfig = None,
        cache=None,
    ):
        if JWTBackend._instance is not None:
            raise RuntimeError("JWTBackend is a singleton. Use get_instance().")

        self.config = config or TokenConfig()
        self.jwt_manager = JWTManager(self.config)
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    @classmethod
    def get_instance(cls) -> "JWTBackend":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()

            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._instance_lock:
            instance = cls._instance
            cls._instance = None

        if instance is not None:
            instance.thread_pool.shutdown(
                wait=False,
                cancel_futures=True,
            )
            instance.jwt_manager.thread_pool.shutdown(
                wait=False,
                cancel_futures=True,
            )

    def _get_verification_key(self):
        return self.jwt_manager._get_verification_key()

    def verify_token_sync(
        self,
        token: str,
        token_type: TokenType = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        return self.jwt_manager.verify_token_sync(
            token,
            token_type,
        )

    def _get_active_roles(self, user) -> List[str]:
        """Return all currently active role codes for a user."""

        return list(
            user.role_assignments.filter(revoked_at__isnull=True)
            .order_by("role__code")
            .values_list("role__code", flat=True)
        )

    def create_tokens_sync(
        self,
        user_id: str,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """Create an access/refresh token pair using database-backed data."""

        User = get_user_model()

        user_uuid = self.jwt_manager._normalize_uuid(
            user_id,
            "user ID",
        )

        session_uuid = self.jwt_manager._normalize_uuid(
            session_id or uuid.uuid4(),
            "session ID",
        )

        with transaction.atomic():
            try:
                user = User.objects.get(pk=user_uuid)
            except User.DoesNotExist:
                raise ValueError("User does not exist.") from None

            if not user.is_active:
                raise ValueError("Inactive users cannot receive tokens.")

            roles = self._get_active_roles(user)

            access_token = self.jwt_manager.generate_access_token(
                user_id=str(user.pk),
                session_id=str(session_uuid),
            )

            refresh_token = self.jwt_manager.generate_refresh_token(
                user_id=str(user.pk),
                session_id=str(session_uuid),
            )

            expires_at = timezone.now() + timedelta(
                seconds=self.config.access_token_expiry
            )

            response = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.config.access_token_expiry,
                "expires_at": expires_at.isoformat(),
                "session_id": str(session_uuid),
                "user": {
                    "id": str(user.pk),
                    "email": user.email,
                    "roles": roles,
                },
            }

        logger.info("Access and refresh token pair created.")

        return response

    def _create_tokens_sync(
        self,
        user_id: str,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """Backward-compatible internal entry point."""

        return self.create_tokens_sync(
            user_id=user_id,
            session_id=session_id,
        )

    async def create_tokens(
        self,
        user_id: str,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """Asynchronous wrapper for synchronous token creation."""

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.thread_pool,
            partial(
                self.create_tokens_sync,
                user_id=user_id,
                session_id=session_id,
            ),
        )

    async def verify_token(
        self,
        token: str,
        token_type: TokenType = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:

        return await self.jwt_manager.verify_token(
            token,
            token_type,
        )

    async def verify_refresh_token(
        self,
        token: str,
    ) -> Optional[Dict[str, Any]]:

        return await self.jwt_manager.verify_refresh_token(token)

    async def is_token_blacklisted(
        self,
        user_id: str,
        token_id: str,
    ) -> bool:

        return await self.jwt_manager.is_token_blacklisted(
            user_id,
            token_id,
        )

    def _refresh_tokens_sync(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Rotate a refresh token atomically.

        Reuse of a consumed token revokes every refresh token belonging
        to the same user session.
        """

        from apps.tcc.models.refresh_token import RefreshToken

        is_valid, payload = self.jwt_manager.verify_token_sync(
            refresh_token,
            TokenType.REFRESH,
        )

        if not is_valid or not payload:
            raise ValueError("Invalid refresh token.")

        user_uuid = self.jwt_manager._normalize_uuid(
            payload["sub"],
            "user ID",
        )

        session_uuid = self.jwt_manager._normalize_uuid(
            payload["session_id"],
            "session ID",
        )

        jti = payload["jti"]
        now = timezone.now()

        failure = None
        response = None

        with transaction.atomic():
            record = (
                RefreshToken.objects.select_for_update()
                .select_related("user")
                .filter(jti=jti)
                .first()
            )

            if record is None:
                failure = "Refresh token does not exist."

            elif record.user_id != user_uuid or record.session_id != session_uuid:
                failure = "Refresh token does not match its stored record."

            elif record.consumed_at is not None:
                RefreshToken.objects.filter(
                    user_id=user_uuid,
                    session_id=session_uuid,
                    revoked_at__isnull=True,
                ).update(revoked_at=now)

                failure = "Refresh token reuse detected. Session revoked."

            elif record.revoked_at is not None:
                failure = "Refresh token has been revoked."

            elif record.expires_at <= now:
                failure = "Refresh token has expired."

            elif not record.user.is_active:
                RefreshToken.objects.filter(
                    user_id=user_uuid,
                    session_id=session_uuid,
                    revoked_at__isnull=True,
                ).update(revoked_at=now)

                failure = "Inactive users cannot refresh tokens."

            else:
                record.consumed_at = now
                record.save(update_fields=["consumed_at"])

                response = self.create_tokens_sync(
                    user_id=str(record.user_id),
                    session_id=str(record.session_id),
                )

        if failure:
            logger.warning(
                "Refresh-token rotation rejected: %s",
                failure,
            )
            raise ValueError(failure)

        logger.info("Refresh token rotated successfully.")

        return response

    def refresh_tokens_sync(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """Public synchronous interface for refresh-token rotation."""

        return self._refresh_tokens_sync(
            refresh_token=refresh_token,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """Asynchronous wrapper for refresh-token rotation."""

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.thread_pool,
            partial(
                self.refresh_tokens_sync,
                refresh_token=refresh_token,
            ),
        )

    async def revoke_refresh_token(
        self,
        user_id: str,
        jti: str,
    ) -> bool:

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.thread_pool,
            partial(
                self.jwt_manager.revoke_refresh_token_sync,
                user_id=user_id,
                jti=jti,
            ),
        )

    def get_token_payload(
        self,
        token: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Decode a JWT without verifying its signature.

        Inspection only. Never use this result for authentication,
        authorization, or permission decisions.
        """

        try:
            return pyjwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_iss": False,
                    "verify_aud": False,
                },
                algorithms=[self.config.algorithm],
            )

        except pyjwt.InvalidTokenError:
            logger.warning("Unable to decode JWT payload.")
            return None

    async def generate_access_token_async(
        self,
        user_id: str,
        session_id: str,
    ) -> str:

        return await self.jwt_manager.generate_access_token_async(
            user_id=user_id,
            session_id=session_id,
        )

    def is_session_active_sync(
        self,
        user_id: str,
        session_id: str,
    ) -> bool:
        """Check whether a session has a usable refresh token."""

        from apps.tcc.models.refresh_token import RefreshToken

        try:
            user_uuid = self.jwt_manager._normalize_uuid(
                user_id,
                "user ID",
            )
            session_uuid = self.jwt_manager._normalize_uuid(
                session_id,
                "session ID",
            )

            return RefreshToken.objects.filter(
                user_id=user_uuid,
                session_id=session_uuid,
                consumed_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists()

        except Exception:
            logger.exception("Session validation failed.")
            return False

    def revoke_session_sync(
        self,
        user_id: str,
        session_id: str,
    ) -> int:
        """Revoke all refresh tokens belonging to one session."""

        from apps.tcc.models.refresh_token import RefreshToken

        user_uuid = self.jwt_manager._normalize_uuid(
            user_id,
            "user ID",
        )

        session_uuid = self.jwt_manager._normalize_uuid(
            session_id,
            "session ID",
        )

        now = timezone.now()

        with transaction.atomic():
            revoked_count = RefreshToken.objects.filter(
                user_id=user_uuid,
                session_id=session_uuid,
                revoked_at__isnull=True,
            ).update(revoked_at=now)

        logger.info(
            "Session revoked. Number of refresh tokens affected: %s",
            revoked_count,
        )

        return revoked_count


def get_jwt_backend() -> JWTBackend:
    return JWTBackend.get_instance()
