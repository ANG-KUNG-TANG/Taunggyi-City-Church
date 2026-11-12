from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import AuthenticationFailed

from common.jwt.jwt_backend import JWTBackend


class AuthenticationService:
    """Business logic for authentication and session management."""

    @staticmethod
    def login(email: str, password: str) -> dict:
        User = get_user_model()

        user = User.objects.filter(
            email__iexact=email,
        ).first()

        if user is None:
            make_password(password)
            raise AuthenticationFailed("Invalid email or password.")

        if not user.check_password(password) or not user.is_active:
            raise AuthenticationFailed("Invalid email or password.")

        jwt_backend = JWTBackend.get_instance()

        try:
            return jwt_backend.create_tokens_sync(
                user_id=str(user.pk),
            )
        except ValueError:
            raise AuthenticationFailed("Unable to authenticate this account.") from None

    @staticmethod
    def refresh(refresh_token: str) -> dict:
        """Validate and rotate a refresh token."""

        jwt_backend = JWTBackend.get_instance()

        try:
            return jwt_backend.refresh_tokens_sync(
                refresh_token=refresh_token,
            )
        except ValueError:
            raise AuthenticationFailed("Authentication failed.") from None

    @staticmethod
    def logout(user_id: str, session_id: str) -> int:
        """Revoke every refresh token belonging to one session."""

        jwt_backend = JWTBackend.get_instance()

        return jwt_backend.revoke_session_sync(
            user_id=user_id,
            session_id=session_id,
        )
