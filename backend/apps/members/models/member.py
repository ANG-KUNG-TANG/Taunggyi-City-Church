import uuid

from django.conf import settings
from django.db import models


class Member(models.Model):
    """
    Church member profile.

    Members are community records and do not authenticate
    or log in to the system.

    Each member belongs to exactly one current zone.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    zone = models.ForeignKey(
        "tcc.Zone",
        on_delete=models.PROTECT,
        related_name="members",
    )

    full_name = models.CharField(
        max_length=200,
    )

    phone = models.CharField(
        max_length=40,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_members",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_members",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "members"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name
