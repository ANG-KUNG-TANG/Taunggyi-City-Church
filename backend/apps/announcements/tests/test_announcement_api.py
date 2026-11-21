"""
Tests for the Announcement API and publication workflow.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models.users import User
from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.announcements.models import Announcement


class AnnouncementAPITestCase(TestCase):
    """Shared setup for Announcement API tests."""

    def setUp(self):
        self.client = APIClient()

        self.pastor = self.create_user_with_role(
            email="pastor@example.com",
            role_code="PASTOR",
            role_name="Pastor",
        )
        self.administrator = self.create_user_with_role(
            email="admin@example.com",
            role_code="ADMINISTRATOR",
            role_name="Administrator",
        )
        self.zone_leader = self.create_user_with_role(
            email="zoneleader@example.com",
            role_code="ZONE_LEADER",
            role_name="Zone Leader",
        )

        self.announcement = Announcement.objects.create(
            title="Church Service Update",
            body="Join us for our Sunday service.",
        )

        self.public_url = "/api/v1/announcements/"
        self.create_url = "/api/v1/announcements/manage/create/"
        self.management_url = "/api/v1/announcements/manage/"
        self.publish_url = (
            f"/api/v1/announcements/manage/{self.announcement.id}/publish/"
        )
        self.archive_url = (
            f"/api/v1/announcements/manage/{self.announcement.id}/archive/"
        )

    def create_user_with_role(self, *, email, role_code, role_name):
        """Create a staff user and assign the requested role."""
        user = User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

        role, _ = Role.objects.get_or_create(
            code=role_code,
            defaults={"name": role_name},
        )

        UserRole.objects.create(user=user, role=role)

        return user


class TestAnnouncementPublicationAPI(AnnouncementAPITestCase):
    """Verify publication permissions and public announcement visibility."""

    def test_draft_announcement_is_not_publicly_visible(self):
        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 200)

        announcement_ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(str(self.announcement.id), announcement_ids)

    def test_pastor_can_publish_announcement(self):
        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.status,
            Announcement.Status.PUBLISHED,
        )
        self.assertEqual(self.announcement.published_by, self.pastor)
        self.assertIsNotNone(self.announcement.published_at)

    def test_administrator_can_publish_announcement(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.status,
            Announcement.Status.PUBLISHED,
        )

    def test_zone_leader_cannot_publish_announcement(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 403)

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.status,
            Announcement.Status.DRAFT,
        )

    def test_published_announcement_is_publicly_visible(self):
        self.client.force_authenticate(user=self.pastor)
        publish_response = self.client.post(
            self.publish_url,
            format="json",
        )
        self.assertEqual(publish_response.status_code, 200)

        self.client.force_authenticate(user=None)
        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 200)

        announcement_ids = [item["id"] for item in response.data["results"]]
        self.assertIn(str(self.announcement.id), announcement_ids)

    def test_draft_announcement_detail_returns_404(self):
        detail_url = f"/api/v1/announcements/public/{self.announcement.id}/"

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 404)

    def test_published_announcement_detail_is_publicly_accessible(self):
        self.client.force_authenticate(user=self.pastor)
        publish_response = self.client.post(
            self.publish_url,
            format="json",
        )
        self.assertEqual(publish_response.status_code, 200)

        self.client.force_authenticate(user=None)
        detail_url = f"/api/v1/announcements/public/{self.announcement.id}/"
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.announcement.id))

    def test_creating_announcement_records_audit_event(self):
        from apps.audit.models.audit_log import AuditLog

        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(
            self.create_url,
            {
                "title": "Youth Fellowship",
                "body": "Join our youth fellowship this weekend.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        audit_event = AuditLog.objects.get(
            entity_id=response.data["id"],
            action=AuditLog.Action.CREATE,
        )

        self.assertEqual(audit_event.actor, self.pastor)
        self.assertEqual(audit_event.entity_type, "Announcement")
        self.assertEqual(audit_event.after_data["status"], "DRAFT")

    def test_publishing_announcement_records_audit_event(self):
        from apps.audit.models.audit_log import AuditLog

        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        audit_event = AuditLog.objects.get(
            entity_id=self.announcement.id,
            action=AuditLog.Action.PUBLISH,
        )

        self.assertEqual(audit_event.actor, self.pastor)
        self.assertEqual(audit_event.entity_type, "Announcement")
        self.assertEqual(audit_event.after_data["status"], "PUBLISHED")

    def test_archiving_announcement_records_audit_event(self):
        from apps.audit.models.audit_log import AuditLog

        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(self.archive_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.announcement.refresh_from_db()
        self.assertEqual(
            self.announcement.status,
            Announcement.Status.ARCHIVED,
        )

        audit_event = AuditLog.objects.get(
            entity_id=self.announcement.id,
            action=AuditLog.Action.UPDATE,
        )

        self.assertEqual(audit_event.actor, self.pastor)
        self.assertEqual(audit_event.entity_type, "Announcement")
        self.assertEqual(audit_event.before_data["status"], "DRAFT")
        self.assertEqual(audit_event.after_data["status"], "ARCHIVED")

    def test_archived_announcement_is_not_publicly_visible(self):
        self.client.force_authenticate(user=self.pastor)
        archive_response = self.client.post(
            self.archive_url,
            format="json",
        )
        self.assertEqual(archive_response.status_code, 200)

        self.client.force_authenticate(user=None)
        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 200)

        announcement_ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(str(self.announcement.id), announcement_ids)

    def test_zone_leader_cannot_create_announcement(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.post(
            self.create_url,
            {
                "title": "Unauthorised Announcement",
                "body": "This should not be created.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_management_list(self):
        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 401)

    def test_pastor_can_access_management_list(self):
        self.client.force_authenticate(user=self.pastor)

        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_invalid_announcement_content_returns_400(self):
        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(
            self.create_url,
            {
                "title": "   ",
                "body": "Announcement body",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
