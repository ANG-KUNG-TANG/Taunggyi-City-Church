import uuid

from django.db import models


class Role(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=40,
        unique=True,
    )
    name = models.CharField(max_length=100)
    description = models.TextField(
        null=True,
        blank=True,
    )
    is_system_role = models.BooleanField(default=True)

    class Meta:
        app_label = "tcc"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"
