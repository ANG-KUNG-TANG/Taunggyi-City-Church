import uuid

from django.conf import settings
from django.db import models


class RefreshToken(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    jti = models.CharField(
        max_length=128,
        unique=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jwt_refresh_tokens",
    )

    session_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    consumed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    revoked_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "jwt_refresh_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "session_id"],
                name="jwt_user_session_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="jwt_expires_idx",
            ),
        ]

    def __str__(self):
        return f"RefreshToken {self.jti}"
