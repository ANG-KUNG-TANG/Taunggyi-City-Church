import uuid
from datetime import timedelta

import jwt
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.accounts.models.users import User
from common.jwt.jwtauth import JWTAuthentication
from common.jwt.jwt_backend import TokenType
from apps.tcc.models.refresh_token import RefreshToken
from rest_framework.test import APIClient
from django.urls import reverse


class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jwt-test@example.com",
            password="test-password",
        )

        self.factory = APIRequestFactory()
        self.authentication = JWTAuthentication()

        self.jwt_backend = self.authentication.jwt_backend
        self.jwt_manager = self.jwt_backend.jwt_manager

        tokens = self.jwt_backend.create_tokens_sync(
            user_id=str(self.user.pk),
        )

        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        self.session_id = tokens["session_id"]

    def authenticate_token(self, token):
        request = self.factory.get(
            "/protected/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        return self.authentication.authenticate(request), request

    def create_signed_token(self, token_type, expires_at):
        now = timezone.now()

        payload = {
            "token_type": token_type,
            "sub": str(self.user.pk),
            "session_id": self.session_id,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.jwt_manager.config.issuer,
            "aud": self.jwt_manager.config.audience,
        }

        return jwt.encode(
            payload,
            self.jwt_manager._get_signing_key(),
            algorithm=self.jwt_manager.config.algorithm,
        )

    def test_valid_access_token_authenticates_user(self):
        result, request = self.authenticate_token(self.access_token)

        self.assertIsNotNone(result)

        authenticated_user, returned_token = result

        self.assertEqual(authenticated_user.pk, self.user.pk)
        self.assertEqual(returned_token, self.access_token)
        self.assertEqual(request.session_id, self.session_id)

    def test_missing_authorization_header_returns_none(self):
        request = self.factory.get("/protected/")

        result = self.authentication.authenticate(request)

        self.assertIsNone(result)

    def test_malformed_token_is_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token("not-a-valid-jwt")

    def test_invalid_authorization_scheme_is_rejected(self):
        request = self.factory.get(
            "/protected/",
            HTTP_AUTHORIZATION="Basic abc123",
        )

        with self.assertRaises(AuthenticationFailed):
            self.authentication.authenticate(request)

    def test_expired_access_token_is_rejected(self):
        expired_token = self.create_signed_token(
            TokenType.ACCESS.value,
            timezone.now() - timedelta(minutes=1),
        )

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(expired_token)

    def test_refresh_token_cannot_authenticate_as_access_token(self):
        refresh_token = self.create_signed_token(
            TokenType.REFRESH.value,
            timezone.now() + timedelta(minutes=5),
        )

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(refresh_token)

    def test_nonexistent_user_is_rejected(self):
        nonexistent_user_id = str(uuid.uuid4())

        token = self.jwt_manager.generate_access_token(
            user_id=nonexistent_user_id,
            session_id=self.session_id,
        )

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(token)

    def test_inactive_user_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(self.access_token)

    def test_access_token_rejected_after_session_revocation(self):
        RefreshToken.objects.filter(
            user_id=self.user.pk,
            session_id=self.session_id,
        ).update(revoked_at=timezone.now())

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(self.access_token)

    def test_access_token_remains_valid_after_successful_refresh_rotation(self):
        rotated_tokens = self.jwt_backend._refresh_tokens_sync(
            self.refresh_token,
        )

        self.assertTrue(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

        result, _ = self.authenticate_token(self.access_token)

        self.assertIsNotNone(result)
        self.assertIn("access_token", rotated_tokens)
        self.assertIn("refresh_token", rotated_tokens)

    def test_refresh_token_replay_revokes_entire_session(self):
        self.jwt_backend._refresh_tokens_sync(self.refresh_token)

        with self.assertRaises(ValueError):
            self.jwt_backend._refresh_tokens_sync(self.refresh_token)

        self.assertFalse(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(self.access_token)

    def test_logout_revokes_entire_session(self):
        revoked_count = self.jwt_backend.revoke_session_sync(
            user_id=str(self.user.pk),
            session_id=self.session_id,
        )

        self.assertGreaterEqual(revoked_count, 1)

        self.assertFalse(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

        with self.assertRaises(AuthenticationFailed):
            self.authenticate_token(self.access_token)


class LoginAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="login-test@example.com",
            password="correct-password",
        )

        self.client = APIClient()
        self.login_url = "/api/v1/auth/login/"

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "login-test@example.com",
                "password": "correct-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("session_id", response.data)
        self.assertEqual(response.data["token_type"], "bearer")
        self.assertEqual(
            response.data["user"]["id"],
            str(self.user.pk),
        )

    def test_login_with_incorrect_password(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "login-test@example.com",
                "password": "wrong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data["error"]["message"],
            "Authentication failed.",
        )

    def test_login_with_nonexistent_email(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "unknown@example.com",
                "password": "some-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data["error"]["message"],
            "Authentication failed.",
        )

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.login_url,
            {
                "email": "login-test@example.com",
                "password": "correct-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_login_requires_email_and_password(self):
        response = self.client.post(
            self.login_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

        details = response.data["error"]["details"]

        self.assertIn("email", details)
        self.assertIn("password", details)


class LogoutAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="logout-test@example.com",
            password="test-password",
        )

        self.jwt_backend = JWTAuthentication().jwt_backend
        self.client = APIClient()
        self.logout_url = "/api/v1/auth/logout/"

        tokens = self.jwt_backend.create_tokens_sync(
            user_id=str(self.user.pk),
        )

        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        self.session_id = tokens["session_id"]

    def authenticate(self, access_token=None):
        token = access_token or self.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_authenticated_user_can_logout(self):
        self.authenticate()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["detail"],
            "Successfully logged out.",
        )

        self.assertFalse(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

    def test_access_token_is_rejected_after_logout(self):
        self.authenticate()

        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, 200)

        protected_response = self.client.get("/api/v1/auth/logout/")

        self.assertEqual(protected_response.status_code, 401)

    def test_unauthenticated_user_cannot_logout(self):
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 401)

        self.assertTrue(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

    def test_logout_does_not_revoke_another_session(self):
        another_session = self.jwt_backend.create_tokens_sync(
            user_id=str(self.user.pk),
        )

        another_session_id = another_session["session_id"]

        self.authenticate()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

        self.assertTrue(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                another_session_id,
            )
        )

    def test_repeated_logout_is_rejected(self):
        self.authenticate()

        first_response = self.client.post(self.logout_url)
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(self.logout_url)
        self.assertEqual(second_response.status_code, 401)


class RefreshAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="refresh-test@example.com",
            password="test-password",
        )

        self.jwt_backend = JWTAuthentication().jwt_backend
        self.client = APIClient()
        self.refresh_url = "/api/v1/auth/refresh/"

        tokens = self.jwt_backend.create_tokens_sync(
            user_id=str(self.user.pk),
        )

        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        self.session_id = tokens["session_id"]

    def refresh(self, token=None):
        return self.client.post(
            self.refresh_url,
            {
                "refresh_token": token or self.refresh_token,
            },
            format="json",
        )

    def test_refresh_token_is_rotated_successfully(self):
        response = self.refresh()

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("session_id", response.data)

        self.assertNotEqual(
            response.data["refresh_token"],
            self.refresh_token,
        )

        self.assertEqual(
            response.data["session_id"],
            self.session_id,
        )

        self.assertTrue(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

    def test_reusing_old_refresh_token_revokes_session(self):
        first_response = self.refresh()

        self.assertEqual(first_response.status_code, 200)

        second_response = self.refresh()

        self.assertEqual(second_response.status_code, 401)

        self.assertFalse(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )

    def test_malformed_refresh_token_is_rejected(self):
        response = self.refresh("not-a-valid-jwt")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data["error"]["message"],
            "Authentication failed.",
        )

    def test_refresh_requires_refresh_token(self):
        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

        self.assertIn(
            "refresh_token",
            response.data["error"]["details"],
        )

    def test_refresh_does_not_accept_access_token(self):
        response = self.refresh(self.access_token)

        self.assertEqual(response.status_code, 401)

        self.assertTrue(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )
