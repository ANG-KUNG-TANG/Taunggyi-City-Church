"""
Service-level tests for MediaService.

Verify authorisation, draft-only media operations,
audit recording, and storage cleanup.
"""

from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.activities.models.activity import Activity
from apps.announcements.models import Announcement
from apps.audit.models.audit_log import AuditLog
from apps.content_media.models.content_media import ContentMedia
from apps.content_media.services.media_service import MediaService


class MediaServiceTests(TestCase):
    """Verify media service behaviour and security."""

    def setUp(self):
        self.activity = Activity.objects.create(
            title="Sunday Worship",
            body="Sunday worship activity.",
        )

        self.announcement = Announcement.objects.create(
            title="Church Update",
            body="Important church announcement.",
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

    @staticmethod
    def create_image():
        """
        Return a small valid PNG image.

        The PNG signature and image data are verified by Pillow.
        """
        import io

        from PIL import Image

        image = Image.new("RGB", (2, 2), color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        return SimpleUploadedFile(
            "church-image.png",
            buffer.getvalue(),
            content_type="image/png",
        )

    def upload_activity_media(self, actor):
        return MediaService.upload_media(
            actor=actor,
            uploaded_file=self.create_image(),
            activity_id=self.activity.id,
        )

    def test_pastor_can_upload_activity_media(self):
        pastor, _ = self.create_user_with_role(
            "pastor@example.com",
            "PASTOR",
            "Pastor",
        )

        media = self.upload_activity_media(pastor)

        self.assertEqual(media.activity, self.activity)
        self.assertIsNone(media.announcement_id)
        self.assertEqual(media.uploaded_by, pastor)
        self.assertEqual(media.category, ContentMedia.Category.IMAGE)
        self.assertEqual(media.mime_type, "image/png")

        self.assertTrue(
            AuditLog.objects.filter(
                actor=pastor,
                entity_type="ContentMedia",
                entity_id=media.id,
                action="CREATE",
            ).exists()
        )

        self.assertTrue(media.file.storage.exists(media.file.name))

    def test_administrator_can_upload_announcement_media(self):
        administrator, _ = self.create_user_with_role(
            "admin@example.com",
            "ADMINISTRATOR",
            "Administrator",
        )

        media = MediaService.upload_media(
            actor=administrator,
            uploaded_file=self.create_image(),
            announcement_id=self.announcement.id,
        )

        self.assertEqual(media.announcement, self.announcement)
        self.assertIsNone(media.activity_id)
        self.assertEqual(media.uploaded_by, administrator)

        self.assertTrue(
            AuditLog.objects.filter(
                actor=administrator,
                entity_type="ContentMedia",
                entity_id=media.id,
                action="CREATE",
            ).exists()
        )

    def test_anonymous_actor_cannot_upload(self):
        with self.assertRaises(PermissionDenied):
            self.upload_activity_media(None)

        self.assertEqual(ContentMedia.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_inactive_user_cannot_upload(self):
        user, _ = self.create_user_with_role(
            "inactive@example.com",
            "PASTOR",
            "Pastor",
        )

        user.is_active = False
        user.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.upload_activity_media(user)

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_zone_leader_cannot_upload(self):
        user, _ = self.create_user_with_role(
            "zoneleader@example.com",
            "ZONE_LEADER",
            "Zone Leader",
        )

        with self.assertRaises(PermissionDenied):
            self.upload_activity_media(user)

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_revoked_manager_cannot_upload(self):
        user, assignment = self.create_user_with_role(
            "revoked@example.com",
            "PASTOR",
            "Pastor",
        )

        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])

        with self.assertRaises(PermissionDenied):
            self.upload_activity_media(user)

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_upload_to_published_activity_is_rejected(self):
        pastor, _ = self.create_user_with_role(
            "published@example.com",
            "PASTOR",
            "Pastor",
        )

        self.activity.status = Activity.Status.PUBLISHED
        self.activity.published_by = pastor
        self.activity.published_at = timezone.now()
        self.activity.save(update_fields=["status", "published_by", "published_at"])

        with self.assertRaises(ValidationError):
            self.upload_activity_media(pastor)

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_upload_to_archived_announcement_is_rejected(self):
        pastor, _ = self.create_user_with_role(
            "archived@example.com",
            "PASTOR",
            "Pastor",
        )

        self.announcement.status = Announcement.Status.ARCHIVED
        self.announcement.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            MediaService.upload_media(
                actor=pastor,
                uploaded_file=self.create_image(),
                announcement_id=self.announcement.id,
            )

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_upload_requires_exactly_one_parent(self):
        pastor, _ = self.create_user_with_role(
            "parent@example.com",
            "PASTOR",
            "Pastor",
        )

        with self.assertRaises(ValidationError):
            MediaService.upload_media(
                actor=pastor,
                uploaded_file=self.create_image(),
            )

        with self.assertRaises(ValidationError):
            MediaService.upload_media(
                actor=pastor,
                uploaded_file=self.create_image(),
                activity_id=self.activity.id,
                announcement_id=self.announcement.id,
            )

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_upload_to_missing_parent_is_rejected(self):
        pastor, _ = self.create_user_with_role(
            "missing@example.com",
            "PASTOR",
            "Pastor",
        )

        with self.assertRaises(Activity.DoesNotExist):
            MediaService.upload_media(
                actor=pastor,
                uploaded_file=self.create_image(),
                activity_id="00000000-0000-0000-0000-000000000001",
            )

        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_delete_media_records_audit_and_removes_file(self):
        pastor, _ = self.create_user_with_role(
            "delete@example.com",
            "PASTOR",
            "Pastor",
        )

        media = self.upload_activity_media(pastor)
        file_name = media.file.name
        storage = media.file.storage
        media_id = media.id

        self.assertTrue(storage.exists(file_name))

        with self.captureOnCommitCallbacks(execute=True):
            MediaService.delete_media(
                actor=pastor,
                media_id=media_id,
            )

        self.assertFalse(ContentMedia.objects.filter(pk=media_id).exists())

        self.assertFalse(storage.exists(file_name))

        self.assertTrue(
            AuditLog.objects.filter(
                actor=pastor,
                entity_type="ContentMedia",
                entity_id=media_id,
                action="UPDATE",
            ).exists()
        )

    def test_zone_leader_cannot_delete_media(self):
        pastor, _ = self.create_user_with_role(
            "owner@example.com",
            "PASTOR",
            "Pastor",
        )

        zone_leader, _ = self.create_user_with_role(
            "deleter@example.com",
            "ZONE_LEADER",
            "Zone Leader",
        )

        media = self.upload_activity_media(pastor)

        with self.assertRaises(PermissionDenied):
            MediaService.delete_media(
                actor=zone_leader,
                media_id=media.id,
            )

        self.assertTrue(ContentMedia.objects.filter(pk=media.id).exists())

    def test_delete_media_from_published_content_is_rejected(self):
        pastor, _ = self.create_user_with_role(
            "published-delete@example.com",
            "PASTOR",
            "Pastor",
        )

        media = self.upload_activity_media(pastor)

        self.activity.status = Activity.Status.PUBLISHED
        self.activity.published_by = pastor
        self.activity.published_at = timezone.now()
        self.activity.save(update_fields=["status", "published_by", "published_at"])

        with self.assertRaises(ValidationError):
            MediaService.delete_media(
                actor=pastor,
                media_id=media.id,
            )

        self.assertTrue(ContentMedia.objects.filter(pk=media.id).exists())

    def test_audit_failure_during_upload_removes_stored_file(self):
        pastor, _ = self.create_user_with_role(
            "audit-failure@example.com",
            "PASTOR",
            "Pastor",
        )

        with patch(
            "apps.content_media.services.media_service.AuditService.record_event",
            side_effect=RuntimeError("Audit failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.upload_activity_media(pastor)

        self.assertEqual(ContentMedia.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)
