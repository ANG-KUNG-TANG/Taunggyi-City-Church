from django.http import JsonResponse
import logging
import asyncio
from asgiref.sync import async_to_sync
from apps.core.jwt.jwt_backend import JWTBackend, TokenType

logger = logging.getLogger(__name__)


class JWTAuthMiddleware:
    """
    Lightweight JWT authentication middleware for both ASGI and WSGI contexts.
    It validates incoming tokens, attaches user claims to the request object,
    and bypasses public routes that must remain open to unauthenticated access.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_backend = JWTBackend.get_instance()

        # Public endpoints that do not require authentication
        self.public_paths = [
            "/tcc/health/",
            "/tcc/auth/login/",
            "/tcc/auth/register/",
            "/tcc/auth/refresh/",
            "/tcc/auth/verify/",
            "/tcc/auth/forgot-password/",
            "/tcc/auth/reset-password/",
            "/tcc/users/",  
            "/admin/",
            "/static/",
            "/media/",
        ]

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def is_public(self, path: str) -> bool:
        """Return True if a path is explicitly whitelisted."""
        return any(path.startswith(p) for p in self.public_paths)

    def extract_token(self, request) -> str | None:
        """Retrieve a JWT from the Authorization header or cookies."""
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if header.startswith("Bearer "):
            return header[7:]

        return request.COOKIES.get("access_token")

    # ---------------------------------------------------------
    # Token verification logic
    # ---------------------------------------------------------

    def _verify_token(self, token: str):
        """
        Handles both sync and async contexts gracefully.
        Returns (is_valid: bool, payload: dict).
        """
        try:
            # ASGI context
            if hasattr(request := None, "_sync_async_hack"):  # noqa
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jwt_backend.verify_token(token, TokenType.ACCESS)
                )
                loop.close()
                return result

            # WSGI context (sync)
            return async_to_sync(self.jwt_backend.verify_token)(
                token, TokenType.ACCESS
            )

        except Exception as exc:
            logger.error(f"Token verification failed: {exc}")
            return False, None

    # ---------------------------------------------------------
    # Main middleware entry point
    # ---------------------------------------------------------

    def __call__(self, request):
        # Allow public endpoints without authentication
        if self.is_public(request.path):
            return self.get_response(request)

        # Extract token
        token = self.extract_token(request)

        if not token:
            logger.warning(f"Authentication required but no token found: {request.path}")
            return JsonResponse(
                {
                    "error": "Authentication required",
                    "message": "Missing or invalid JWT token.",
                },
                status=401,
            )

        # Validate token
        is_valid, payload = self._verify_token(token)

        if not is_valid:
            logger.warning(f"Invalid token for path: {request.path}")
            return JsonResponse(
                {"error": "Invalid or expired token"},
                status=401,
            )

        # Attach claims to request
        request.user_id = payload.get("sub")
        request.user_email = payload.get("email")
        request.user_roles = payload.get("roles", [])
        request.jti = payload.get("jti")
        request.session_id = payload.get("session_id")

        logger.debug(f"Authenticated user {request.user_id} → {request.path}")

        return self.get_response(request)
