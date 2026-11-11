"""
Individual member attendance records.
"""

import uuid

from django.conf import settings
from django.db import models


class MemberAttendance(models.Model):
    """Records attendance for one member in one session."""

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        "tcc.AttendanceSession",
        on_delete=models.PROTECT,
        related_name="member_attendance",
    )

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_member_attendance",
    )

    recorded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_member_attendance",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        app_label = "tcc"
        db_table = "member_attendance"
        ordering = ["member__full_name"]

        constraints = [
            models.UniqueConstraint(
                fields=["session", "member"],
                name="unique_member_attendance_per_session",
            ),
        ]

        indexes = [
            models.Index(
                fields=["session", "status"],
                name="member_att_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.member} - {self.status}"
