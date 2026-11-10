"""
Tests for the Activity API and publication workflow.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models.users import User
from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole


class ActivityAPITestCase(TestCase):
    """Shared setup for Activity API tests."""

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

        UserRole.objects.create(
            user=user,
            role=role,
        )

        return user


class TestActivityPublicationAPI(ActivityAPITestCase):
    """Verify publication permissions and public activity visibility."""

    def setUp(self):
        super().setUp()

        from apps.tcc.models import Activity

        self.activity = Activity.objects.create(
            title="Sunday Worship",
            body="Join us for Sunday worship.",
        )

        self.public_url = "/api/v1/activities/"
        self.publish_url = f"/api/v1/activities/manage/{self.activity.id}/publish/"

    def test_draft_activity_is_not_publicly_visible(self):
        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            any(item["id"] == str(self.activity.id) for item in response.data)
        )

    def test_pastor_can_publish_activity(self):
        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.activity.refresh_from_db()

        self.assertEqual(
            self.activity.status,
            self.activity.Status.PUBLISHED,
        )
        self.assertEqual(self.activity.published_by, self.pastor)
        self.assertIsNotNone(self.activity.published_at)

    def test_administrator_can_publish_activity(self):
        self.client.force_authenticate(user=self.administrator)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.activity.refresh_from_db()

        self.assertEqual(
            self.activity.status,
            self.activity.Status.PUBLISHED,
        )

    def test_zone_leader_cannot_publish_activity(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 403)

        self.activity.refresh_from_db()

        self.assertEqual(
            self.activity.status,
            self.activity.Status.DRAFT,
        )

    def test_published_activity_is_publicly_visible(self):
        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(user=None)

        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any(item["id"] == str(self.activity.id) for item in response.data)
        )

    def test_publishing_activity_records_audit_event(self):
        from apps.audit.models.audit_log import AuditLog

        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(self.publish_url, format="json")

        self.assertEqual(response.status_code, 200)

        audit_event = AuditLog.objects.get(
            entity_id=self.activity.id,
            action=AuditLog.Action.PUBLISH,
        )

        self.assertEqual(audit_event.actor, self.pastor)
        self.assertEqual(audit_event.entity_type, "Activity")
        self.assertEqual(audit_event.after_data["status"], "PUBLISHED")

    def test_creating_activity_records_audit_event(self):
        from apps.audit.models.audit_log import AuditLog

        self.client.force_authenticate(user=self.pastor)

        response = self.client.post(
            "/api/v1/activities/manage/create/",
            {
                "title": "Youth Fellowship",
                "body": "Join our youth fellowship.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        activity_id = response.data["id"]

        audit_event = AuditLog.objects.get(
            entity_id=activity_id,
            action=AuditLog.Action.CREATE,
        )

        self.assertEqual(audit_event.actor, self.pastor)
        self.assertEqual(audit_event.entity_type, "Activity")
        self.assertEqual(audit_event.after_data["status"], "DRAFT")

    def test_archiving_activity_records_audit_event(self):
        from apps.audit.models.audit_log import AuditLog

        self.client.force_authenticate(user=self.pastor)

        archive_url = f"/api/v1/activities/manage/{self.activity.id}/archive/"

        response = self.client.post(archive_url, format="json")

        self.assertEqual(response.status_code, 200)

        self.activity.refresh_from_db()

        self.assertEqual(
            self.activity.status,
            self.activity.Status.ARCHIVED,
        )

        audit_event = AuditLog.objects.get(
            entity_id=self.activity.id,
            action=AuditLog.Action.UPDATE,
        )

        self.assertEqual(audit_event.actor, self.pastor)
        self.assertEqual(audit_event.entity_type, "Activity")
        self.assertEqual(audit_event.before_data["status"], "DRAFT")
        self.assertEqual(audit_event.after_data["status"], "ARCHIVED")

    def test_zone_leader_cannot_archive_activity(self):
        self.client.force_authenticate(user=self.zone_leader)

        archive_url = f"/api/v1/activities/manage/{self.activity.id}/archive/"

        response = self.client.post(archive_url, format="json")

        self.assertEqual(response.status_code, 403)

        self.activity.refresh_from_db()

        self.assertEqual(
            self.activity.status,
            self.activity.Status.DRAFT,
        )

    def test_archived_activity_is_not_publicly_visible(self):
        self.client.force_authenticate(user=self.pastor)

        archive_url = f"/api/v1/activities/manage/{self.activity.id}/archive/"

        archive_response = self.client.post(
            archive_url,
            format="json",
        )

        self.assertEqual(archive_response.status_code, 200)

        self.client.force_authenticate(user=None)

        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 200)

        activity_ids = [str(item["id"]) for item in response.data]

        self.assertNotIn(str(self.activity.id), activity_ids)
