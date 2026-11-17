from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.accounts.models.users import User
from apps.tcc.models.refresh_token import RefreshToken
from common.jwt.jwt_backend import JWTBackend


@skipUnlessDBFeature("has_select_for_update")
class PostgreSQLRefreshTokenConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("This concurrency test requires PostgreSQL.")

        self.user = User.objects.create_user(
            email="jwt-concurrency@example.com",
            password="test-password",
        )

        self.jwt_backend = JWTBackend.get_instance()

        tokens = self.jwt_backend.create_tokens_sync(
            user_id=str(self.user.pk),
        )

        self.refresh_token = tokens["refresh_token"]
        self.session_id = tokens["session_id"]

    def rotate_refresh_token(self, barrier):
        close_old_connections()

        try:
            barrier.wait(timeout=15)

            try:
                result = self.jwt_backend.refresh_tokens_sync(
                    refresh_token=self.refresh_token,
                )
                return "success", result
            except ValueError as exc:
                return "rejected", str(exc)
        finally:
            connections.close_all()

    def test_simultaneous_refresh_token_reuse_revokes_session(self):
        barrier = Barrier(2)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self.rotate_refresh_token, barrier) for _ in range(2)
            ]
            results = [future.result(timeout=30) for future in futures]

        successes = [result for status, result in results if status == "success"]
        rejections = [result for status, result in results if status == "rejected"]

        self.assertEqual(
            len(successes),
            1,
            msg=f"Expected exactly one successful rotation; got {results}",
        )
        self.assertEqual(
            len(rejections),
            1,
            msg=f"Expected exactly one rejected rotation; got {results}",
        )
        self.assertIn("reuse detected", rejections[0].lower())

        session_tokens = RefreshToken.objects.filter(
            user_id=self.user.pk,
            session_id=self.session_id,
        )

        self.assertTrue(session_tokens.exists())
        self.assertTrue(session_tokens.filter(consumed_at__isnull=False).exists())
        self.assertFalse(session_tokens.filter(revoked_at__isnull=True).exists())

        self.assertFalse(
            self.jwt_backend.is_session_active_sync(
                str(self.user.pk),
                self.session_id,
            )
        )
