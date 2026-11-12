"""
DRF-Compatible JWT Authentication Class
FIXED: Includes proper role and permission handling
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging
import re
import jwt as pyjwt
from common.jwt.jwt_backend import JWTBackend, TokenType
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseAuthentication):
    """
    Token-based authentication using JWT.

    Clients should authenticate by passing the token in the Authorization HTTP header:
    Authorization: Bearer <token>
    """

    keyword = "Bearer"

    def authenticate_header(self, request):
        """Return the authentication challenge for unauthenticated requests."""
        return self.keyword

    def __init__(self):
        super().__init__()
        self.jwt_backend = JWTBackend.get_instance()
        logger.debug("JWTAuthentication initialized")

    def authenticate(self, request):
        """
        Authenticate the request and return (user, token) tuple.
        Returns None if no token found (allows other authenticators to try).
        """
        # Extract token from request
        token = self.extract_token(request)

        if token is None:
            logger.debug("No token found in request")
            return None

        # Validate token format before attempting verification
        if not self.is_valid_jwt_format(token):
            logger.warning("Malformed JWT token received")
            raise AuthenticationFailed("Invalid token format")

        try:
            # Use the backend's verification method directly
            is_valid, payload = self.jwt_backend.verify_token_sync(
                token, TokenType.ACCESS
            )

            if not is_valid or not payload:
                logger.warning("Token verification failed")
                raise AuthenticationFailed("Invalid or expired token")

            # Ensure 'sub' is string
            if "sub" in payload and not isinstance(payload["sub"], str):
                payload["sub"] = str(payload["sub"])

            # Backward compatibility: Ensure role and permission fields exist
            if "role" not in payload:
                payload["role"] = payload.get("roles", ["member"])[0]
            if "is_superuser" not in payload:
                payload["is_superuser"] = payload.get("role") in [
                    "super_admin",
                    "admin",
                ]
            if "is_staff" not in payload:
                payload["is_staff"] = payload.get("role") in [
                    "super_admin",
                    "admin",
                    "staff",
                ]

            logger.info(
                f"Token verified for user: {payload.get('email')} "
                f"with role: {payload.get('role')}, "
                f"is_superuser: {payload.get('is_superuser')}"
            )

            # Create user object from payload
            user = self.get_database_user(payload)

            # Attach extra JWT data to request
            request.user_id = payload.get("sub")
            request.user_email = payload.get("email")
            request.user_role = payload.get("role")
            request.user_roles = payload.get("roles", [payload.get("role")])
            request.is_superuser = payload.get("is_superuser", False)
            request.is_staff = payload.get("is_staff", False)
            request.jti = payload.get("jti")
            request.session_id = payload.get("session_id")

            logger.info(
                f"Authentication successful for user {user.email} "
                f"with role {payload.get('role')}"
            )
            return (user, token)

        except pyjwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise AuthenticationFailed("Token expired")
        except pyjwt.DecodeError:
            logger.warning("JWT decoding failed")
            raise AuthenticationFailed("Invalid token format")
        except pyjwt.InvalidTokenError:
            logger.warning("JWT validation failed")
            raise AuthenticationFailed("Invalid token")
        except AuthenticationFailed:
            raise
        except Exception:
            logger.error("Unexpected JWT authentication error")
            raise AuthenticationFailed("Authentication failed")

    def is_valid_jwt_format(self, token: str) -> bool:
        """
        Validate the exact JWT value without modifying or repairing it.
        """
        if not isinstance(token, str) or len(token) < 10:
            return False

        parts = token.split(".")
        if len(parts) != 3:
            return False

        base64url_pattern = r"^[A-Za-z0-9_-]+$"
        return all(re.fullmatch(base64url_pattern, part) is not None for part in parts)

    def extract_token(self, request):
        """
        Extract a JWT from a strict Bearer Authorization header or a
        supported authentication cookie.

        A malformed Authorization header is rejected rather than ignored.
        Cookie-based authentication remains supported.
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header:
            parts = auth_header.strip().split()

            if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
                logger.warning("Authorization header has an invalid Bearer format")
                raise AuthenticationFailed("Invalid authorization header")

            return parts[1]

        cookie_names = [
            "access_token",
            "token",
            "jwt_token",
            "auth_token",
        ]

        for cookie_name in cookie_names:
            if cookie_name in request.COOKIES:
                return request.COOKIES[cookie_name]

        return None

    def get_database_user(self, payload: dict):
        """Resolve the JWT subject to the actual database user."""

        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationFailed("Token is missing user identifier")

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
    Optional JWT authentication - doesn't fail if no token is provided.

    Useful for endpoints that work for both authenticated and anonymous users.
    """

    def authenticate(self, request):
        return super().authenticate(request)
