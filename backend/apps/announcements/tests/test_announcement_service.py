"""
Service-level tests for AnnouncementService.

Verify authorisation, lifecycle validation, audit recording,
and transactional integrity.
"""

from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.announcements.models import Announcement
from apps.announcements.services.announcement_service import (
    AnnouncementService,
)
from apps.audit.models.audit_log import AuditLog


class AnnouncementServiceTests(TestCase):
    """Verify announcement service behaviour and security."""

    def setUp(self):
        self.announcement = Announcement.objects.create(
            title="Sunday Worship",
            body="Join us for Sunday worship.",
            status=Announcement.Status.DRAFT,
        )

    def create_user_with_role(self, email, role_code, role_name):
        user = User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

        role, _ = Role.objects.get_or_create(
            code=role_code,
            defaults={"name": role_name},
        )

        assignment = UserRole.objects.create(
            user=user,
            role=role,
        )

        return user, assignment

    def invoke_all_operations(self, actor):
        """Attempt every mutating operation using the supplied actor."""

        operations = [
            (
                "create",
                lambda: AnnouncementService.create_announcement(
                    actor=actor,
                    title="New Announcement",
                    body="Announcement description.",
                ),
            ),
            (
                "update",
                lambda: AnnouncementService.update_announcement(
                    actor=actor,
                    announcement_id=self.announcement.id,
                    title="Updated Announcement",
                    body="Updated description.",
                ),
            ),
            (
                "publish",
                lambda: AnnouncementService.publish_announcement(
                    actor=actor,
                    announcement_id=self.announcement.id,
                ),
            ),
            (
                "archive",
                lambda: AnnouncementService.archive_announcement(
                    actor=actor,
                    announcement_id=self.announcement.id,
                ),
            ),
        ]

        initial_count = Announcement.objects.count()
        initial_audit_count = AuditLog.objects.count()

        for operation_name, operation in operations:
            with self.subTest(operation=operation_name):
                with self.assertRaises(PermissionDenied):
                    operation()

                self.announcement.refresh_from_db()

                self.assertEqual(
                    Announcement.objects.count(),
                    initial_count,
                )
                self.assertEqual(
                    AuditLog.objects.count(),
                    initial_audit_count,
                )
                self.assertEqual(
                    self.announcement.title,
                    "Sunday Worship",
                )
                self.assertEqual(
                    self.announcement.body,
                    "Join us for Sunday worship.",
                )
                self.assertEqual(
                    self.announcement.status,
                    Announcement.Status.DRAFT,
                )

    def test_anonymous_actor_is_rejected(self):
        self.invoke_all_operations(None)

    def test_inactive_user_is_rejected(self):
        user, _ = self.create_user_with_role(
            "inactive@example.com",
            "PASTOR",
            "Pastor",
        )
        user.is_active = False
        user.save(update_fields=["is_active"])

        self.invoke_all_operations(user)

    def test_zone_leader_is_rejected(self):
        user, _ = self.create_user_with_role(
            "zoneleader@example.com",
            "ZONE_LEADER",
            "Zone Leader",
        )

        self.invoke_all_operations(user)

    def test_revoked_manager_assignment_is_rejected(self):
        user, assignment = self.create_user_with_role(
            "revoked@example.com",
            "PASTOR",
            "Pastor",
        )
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])

        self.invoke_all_operations(user)

    def test_pastor_can_use_all_operations(self):
        self._assert_manager_lifecycle(
            email="pastor@example.com",
            role_code="PASTOR",
            role_name="Pastor",
        )

    def test_administrator_can_use_all_operations(self):
        self._assert_manager_lifecycle(
            email="admin@example.com",
            role_code="ADMINISTRATOR",
            role_name="Administrator",
        )

    def _assert_manager_lifecycle(self, *, email, role_code, role_name):
        user, _ = self.create_user_with_role(
            email,
            role_code,
            role_name,
        )

        created = AnnouncementService.create_announcement(
            actor=user,
            title="New Announcement",
            body="Created through the service.",
        )

        updated = AnnouncementService.update_announcement(
            actor=user,
            announcement_id=created.id,
            title="Updated Announcement",
            body="Updated through the service.",
        )

        published = AnnouncementService.publish_announcement(
            actor=user,
            announcement_id=updated.id,
        )

        archived = AnnouncementService.archive_announcement(
            actor=user,
            announcement_id=published.id,
        )

        self.assertEqual(
            archived.status,
            Announcement.Status.ARCHIVED,
        )
        self.assertEqual(
            AuditLog.objects.filter(actor=user).count(),
            4,
        )

    def test_create_normalises_content(self):
        user, _ = self.create_user_with_role(
            "normalise@example.com",
            "PASTOR",
            "Pastor",
        )

        announcement = AnnouncementService.create_announcement(
            actor=user,
            title="  Church Update  ",
            body="  Important information.  ",
        )

        self.assertEqual(announcement.title, "Church Update")
        self.assertEqual(announcement.body, "Important information.")
        self.assertEqual(
            announcement.status,
            Announcement.Status.DRAFT,
        )

    def test_empty_title_is_rejected(self):
        user, _ = self.create_user_with_role(
            "emptytitle@example.com",
            "PASTOR",
            "Pastor",
        )

        with self.assertRaises(ValidationError):
            AnnouncementService.create_announcement(
                actor=user,
                title="   ",
                body="Valid announcement body.",
            )

        self.assertEqual(
            Announcement.objects.count(),
            1,
        )

    def test_title_longer_than_200_characters_is_rejected(self):
        user, _ = self.create_user_with_role(
            "longtitle@example.com",
            "PASTOR",
            "Pastor",
        )

        with self.assertRaises(ValidationError):
            AnnouncementService.create_announcement(
                actor=user,
                title="A" * 201,
                body="Valid announcement body.",
            )

        self.assertEqual(Announcement.objects.count(), 1)

    def test_empty_body_is_rejected(self):
        user, _ = self.create_user_with_role(
            "emptybody@example.com",
            "PASTOR",
            "Pastor",
        )

        with self.assertRaises(ValidationError):
            AnnouncementService.create_announcement(
                actor=user,
                title="Valid title",
                body="   ",
            )

        self.assertEqual(Announcement.objects.count(), 1)

    def test_unchanged_update_does_not_create_audit_event(self):
        user, _ = self.create_user_with_role(
            "noop@example.com",
            "PASTOR",
            "Pastor",
        )

        initial_audit_count = AuditLog.objects.count()

        result = AnnouncementService.update_announcement(
            actor=user,
            announcement_id=self.announcement.id,
            title=self.announcement.title,
            body=self.announcement.body,
        )

        self.assertEqual(result.id, self.announcement.id)
        self.assertEqual(
            AuditLog.objects.count(),
            initial_audit_count,
        )

    def test_archived_announcement_cannot_be_updated(self):
        user, _ = self.create_user_with_role(
            "archiveedit@example.com",
            "PASTOR",
            "Pastor",
        )

        self.announcement.status = Announcement.Status.ARCHIVED
        self.announcement.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            AnnouncementService.update_announcement(
                actor=user,
                announcement_id=self.announcement.id,
                title="Updated title",
            )

    def test_archived_announcement_cannot_be_published(self):
        user, _ = self.create_user_with_role(
            "archivepublish@example.com",
            "PASTOR",
            "Pastor",
        )

        self.announcement.status = Announcement.Status.ARCHIVED
        self.announcement.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            AnnouncementService.publish_announcement(
                actor=user,
                announcement_id=self.announcement.id,
            )

    def test_already_published_announcement_cannot_be_published_again(self):
        user, _ = self.create_user_with_role(
            "republish@example.com",
            "PASTOR",
            "Pastor",
        )

        AnnouncementService.publish_announcement(
            actor=user,
            announcement_id=self.announcement.id,
        )

        initial_audit_count = AuditLog.objects.count()

        with self.assertRaises(ValidationError):
            AnnouncementService.publish_announcement(
                actor=user,
                announcement_id=self.announcement.id,
            )

        self.assertEqual(
            AuditLog.objects.count(),
            initial_audit_count,
        )

    def test_already_archived_announcement_cannot_be_archived_again(self):
        user, _ = self.create_user_with_role(
            "rearchive@example.com",
            "PASTOR",
            "Pastor",
        )

        AnnouncementService.archive_announcement(
            actor=user,
            announcement_id=self.announcement.id,
        )

        initial_audit_count = AuditLog.objects.count()

        with self.assertRaises(ValidationError):
            AnnouncementService.archive_announcement(
                actor=user,
                announcement_id=self.announcement.id,
            )

        self.assertEqual(
            AuditLog.objects.count(),
            initial_audit_count,
        )

    def test_missing_announcement_raises_does_not_exist(self):
        user, _ = self.create_user_with_role(
            "missing@example.com",
            "PASTOR",
            "Pastor",
        )

        missing_id = "00000000-0000-0000-0000-000000000001"

        operations = [
            lambda: AnnouncementService.update_announcement(
                actor=user,
                announcement_id=missing_id,
                title="Updated title",
            ),
            lambda: AnnouncementService.publish_announcement(
                actor=user,
                announcement_id=missing_id,
            ),
            lambda: AnnouncementService.archive_announcement(
                actor=user,
                announcement_id=missing_id,
            ),
        ]

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(Announcement.DoesNotExist):
                    operation()

    def test_audit_failure_rolls_back_announcement_creation(self):
        user, _ = self.create_user_with_role(
            "auditcreate@example.com",
            "PASTOR",
            "Pastor",
        )

        initial_count = Announcement.objects.count()

        with patch(
            "apps.announcements.services.announcement_service."
            "AuditService.record_event",
            side_effect=RuntimeError("Audit service failure"),
        ):
            with self.assertRaises(RuntimeError):
                AnnouncementService.create_announcement(
                    actor=user,
                    title="Transactional Announcement",
                    body="This creation must roll back.",
                )

        self.assertEqual(
            Announcement.objects.count(),
            initial_count,
        )

    def test_audit_failure_rolls_back_announcement_update(self):
        user, _ = self.create_user_with_role(
            "auditupdate@example.com",
            "PASTOR",
            "Pastor",
        )

        with patch(
            "apps.announcements.services.announcement_service."
            "AuditService.record_event",
            side_effect=RuntimeError("Audit service failure"),
        ):
            with self.assertRaises(RuntimeError):
                AnnouncementService.update_announcement(
                    actor=user,
                    announcement_id=self.announcement.id,
                    title="This update must roll back",
                )

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.title,
            "Sunday Worship",
        )

    def test_audit_failure_rolls_back_publication(self):
        user, _ = self.create_user_with_role(
            "auditpublish@example.com",
            "PASTOR",
            "Pastor",
        )

        with patch(
            "apps.announcements.services.announcement_service."
            "AuditService.record_event",
            side_effect=RuntimeError("Audit service failure"),
        ):
            with self.assertRaises(RuntimeError):
                AnnouncementService.publish_announcement(
                    actor=user,
                    announcement_id=self.announcement.id,
                )

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.status,
            Announcement.Status.DRAFT,
        )
        self.assertIsNone(self.announcement.published_by)
        self.assertIsNone(self.announcement.published_at)

    def test_audit_failure_rolls_back_archival(self):
        user, _ = self.create_user_with_role(
            "auditarchive@example.com",
            "PASTOR",
            "Pastor",
        )

        with patch(
            "apps.announcements.services.announcement_service."
            "AuditService.record_event",
            side_effect=RuntimeError("Audit service failure"),
        ):
            with self.assertRaises(RuntimeError):
                AnnouncementService.archive_announcement(
                    actor=user,
                    announcement_id=self.announcement.id,
                )

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.status,
            Announcement.Status.DRAFT,
        )
