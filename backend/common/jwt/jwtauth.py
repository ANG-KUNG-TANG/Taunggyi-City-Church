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
from django.conf import settings
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
            logger.error(f"Invalid JWT format. Token length: {len(token)}")
            logger.error(
                f"Token preview: '{token[:100] if len(token) > 100 else token}'"
            )
            raise AuthenticationFailed("Invalid token format")

        logger.debug(f"Token extracted, length: {len(token)}")

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
        except pyjwt.DecodeError as e:
            logger.error(f"Token decode error: {e}")
            logger.error(f"Token that failed: '{token[:100]}...'")
            raise AuthenticationFailed("Invalid token format")
        except pyjwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise AuthenticationFailed("Invalid token")
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}", exc_info=True)
            raise AuthenticationFailed("Authentication failed")

    def is_valid_jwt_format(self, token: str) -> bool:
        """
        Validate that token has the correct JWT format (3 parts separated by dots)
        """
        if not token or not isinstance(token, str):
            logger.error("Token is empty or not a string")
            return False

        # Clean the token - remove any quotes
        token = token.strip().strip("\"'")

        if len(token) < 10:
            logger.error(f"Token too short: {len(token)} chars")
            return False

        # JWT should have exactly 2 dots (3 parts)
        parts = token.split(".")
        if len(parts) != 3:
            logger.error(f"JWT has {len(parts)} parts, expected 3")
            return False

        # Each part should be non-empty
        for i, part in enumerate(parts):
            if not part:
                logger.error(f"JWT part {i} is empty")
                return False

            if " " in part:
                logger.error(f"JWT part {i} contains spaces")
                return False

        # Check for base64url characters
        base64url_pattern = r"^[A-Za-z0-9_-]+$"
        for i, part in enumerate(parts):
            if not re.match(base64url_pattern, part):
                logger.error(f"JWT part {i} contains invalid base64url characters")
                return False

        return True

    def extract_token(self, request):
        """
        Extract JWT token from request headers or cookies.

        FIXED: Better token extraction with validation
        """
        token = None

        # Try Authorization header first
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header:
            logger.debug(f"Raw Authorization header: '{auth_header[:100]}'")

            # Clean up the header
            auth_header = auth_header.strip()

            # Handle different formats
            if auth_header.lower().startswith("bearer "):
                # Extract token after "Bearer "
                token = auth_header[7:].strip()
            elif " " in auth_header:
                # Try to extract token from other formats
                parts = auth_header.split()
                if len(parts) >= 2:
                    # Take the last part if there are multiple parts
                    token = parts[-1].strip()
                else:
                    token = auth_header.strip()
            else:
                # No bearer prefix, might be just the token
                token = auth_header.strip()

            # Clean up the token
            if token:
                # Remove any quotes
                token = token.strip("\"'")

                # Remove any trailing spaces or newlines
                token = token.strip()

                # Log for debugging
                logger.debug(f"Extracted token from header (length: {len(token)})")

                # Validate it looks like a JWT
                if "." not in token:
                    logger.warning(
                        "Extracted token doesn't contain dots, might not be a JWT"
                    )
                    token = None

        # If no token from header, try cookies
        if not token:
            # Try different cookie names
            cookie_names = ["access_token", "token", "jwt_token", "auth_token"]
            for cookie_name in cookie_names:
                if cookie_name in request.COOKIES:
                    token = request.COOKIES[cookie_name]
                    logger.debug(
                        f"Found token in cookie '{cookie_name}' (length: {len(token)})"
                    )
                    break

        # Final cleanup
        if token:
            token = token.strip().strip("\"'").strip()

            # Basic validation
            if len(token) < 10:
                logger.error(f"Token too short after extraction: {len(token)} chars")
                return None

            # Check for common issues
            if "\n" in token or "\r" in token:
                logger.error("Token contains newline characters")
                token = token.replace("\n", "").replace("\r", "")

            if " " in token:
                logger.warning("Token contains spaces, removing them")
                # If it's a multi-part token with spaces, take the part that looks like a JWT
                parts = token.split()
                for part in parts:
                    if "." in part and len(part) > 20:
                        token = part
                        break

        return token

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
        """
        Try to authenticate, but return None instead of failing.
        """
        try:
            return super().authenticate(request)
        except AuthenticationFailed as e:
            logger.debug(
                f"Optional JWT authentication failed: {e}, allowing anonymous access"
            )
            return None
