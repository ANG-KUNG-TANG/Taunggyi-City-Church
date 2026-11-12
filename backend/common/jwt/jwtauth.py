"""
Django REST Framework JWT Authentication.

Authenticates users using signed JWT access tokens.
User identity and account status are resolved from the database.

Authorization is handled separately through database-backed
permission classes.
"""

import logging
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from common.jwt.jwt_backend import JWTBackend, TokenType


logger = logging.getLogger(__name__)


class JWTAuthentication(BaseAuthentication):
    """
    Authenticate requests using:

        Authorization: Bearer <access_token>

    JWT claims are used for authentication, not authorization.

    User roles and permissions must be resolved through
    database-backed permission classes.
    """

    keyword = "Bearer"

    def __init__(self):
        super().__init__()
        self.jwt_backend = JWTBackend.get_instance()

    def authenticate_header(self, request):
        """Return the authentication challenge."""
        return self.keyword

    def authenticate(self, request):
        """
        Return (user, token) when authentication succeeds.

        Return None when no Authorization header is provided,
        allowing other configured authenticators to run.
        """

        token = self.extract_token(request)

        if token is None:
            return None

        if not self.is_valid_jwt_format(token):
            logger.warning("Malformed JWT received")
            raise AuthenticationFailed("Invalid token format")

        try:
            is_valid, payload = self.jwt_backend.verify_token_sync(
                token,
                TokenType.ACCESS,
            )

            if not is_valid or not payload:
                logger.warning("JWT authentication rejected")
                raise AuthenticationFailed("Invalid or expired token")

            if not self.jwt_backend.is_session_active_sync(
                user_id=payload.get("sub"),
                session_id=payload.get("session_id"),
            ):
                logger.warning("JWT authentication rejected: inactive session")
                raise AuthenticationFailed("Session is no longer active")

            user = self.get_database_user(payload)

            # Keep validated token metadata available for
            # session-management operations.
            request.jwt_payload = payload
            request.jti = payload.get("jti")
            request.session_id = payload.get("session_id")

            logger.debug("JWT authentication successful")

            return user, token

        except AuthenticationFailed:
            raise

        except Exception:
            logger.exception("Unexpected JWT authentication error")
            raise AuthenticationFailed("Authentication failed")

    def extract_token(self, request):
        """
        Extract a Bearer token from the Authorization header.

        Cookie-based JWT authentication is intentionally disabled
        until proper CSRF protection is implemented.
        """

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header:
            return None

        parts = auth_header.strip().split()

        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            logger.warning("Invalid Authorization header format")
            raise AuthenticationFailed("Invalid authorization header")

        return parts[1]

    @staticmethod
    def is_valid_jwt_format(token: str) -> bool:
        """Validate the three-part JWT structure."""

        if not isinstance(token, str) or len(token) < 10:
            return False

        parts = token.split(".")

        if len(parts) != 3:
            return False

        base64url_pattern = r"^[A-Za-z0-9_-]+$"

        return all(re.fullmatch(base64url_pattern, part) is not None for part in parts)

    @staticmethod
    def get_database_user(payload: dict):
        """
        Resolve the JWT subject to an active database user.

        No role or privilege information is taken from JWT claims.
        """

        user_id = payload.get("sub")

        if not isinstance(user_id, str) or not user_id.strip():
            raise AuthenticationFailed("Token is missing a valid user identifier")

        User = get_user_model()

        try:
            user = User._default_manager.get(pk=user_id)

        except (
            User.DoesNotExist,
            DjangoValidationError,
            ValueError,
            TypeError,
        ):
            raise AuthenticationFailed("User associated with token does not exist")

        if not user.is_active:
            raise AuthenticationFailed("User account is inactive")

        return user


class JWTAuthenticationOptional(JWTAuthentication):
    """
    Optional JWT authentication.

    Requests without a Bearer token remain anonymous.
    Invalid tokens are still rejected.
    """

    pass
