import uuid

from django.conf import settings
from django.db import models


class UserRole(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )

    role = models.ForeignKey(
        "tcc.Role",
        on_delete=models.PROTECT,
        related_name="user_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "tcc"
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.user} - {self.role.code}"
