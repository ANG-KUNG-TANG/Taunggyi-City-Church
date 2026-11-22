from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models.users import User
from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.activities.models.activity import Activity
from apps.announcements.models.announcement import Announcement
from apps.content_media.models.content_media import ContentMedia
from django.utils import timezone


class MediaAPITestCase(TestCase):
    """Shared setup for content media API tests."""

    def setUp(self):
        self.client = APIClient()

        self.pastor = self.create_user("pastor@example.com", "PASTOR", "Pastor")
        self.admin = self.create_user(
            "admin@example.com", "ADMINISTRATOR", "Administrator"
        )
        self.zone_leader = self.create_user(
            "zone@example.com", "ZONE_LEADER", "Zone Leader"
        )

        self.activity = Activity.objects.create(
            title="Church Retreat",
            body="Annual church retreat.",
        )
        self.announcement = Announcement.objects.create(
            title="Service Update",
            body="Sunday service information.",
        )

        self.activity_media_url = f"/api/v1/activities/manage/{self.activity.id}/media/"
        self.announcement_media_url = (
            f"/api/v1/announcements/manage/{self.announcement.id}/media/"
        )

    def create_user(self, email, role_code, role_name):
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

    def create_image(self):
        image = Image.new("RGB", (10, 10), color="red")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        return SimpleUploadedFile(
            "test-image.jpg",
            buffer.read(),
            content_type="image/jpeg",
        )

    def upload_media(self, url, user=None):
        self.client.force_authenticate(user=user or self.pastor)
        return self.client.post(
            url,
            {"file": self.create_image()},
            format="multipart",
        )

    def publish_activity(self):
        self.activity.status = Activity.Status.PUBLISHED
        self.activity.published_by = self.pastor
        self.activity.published_at = timezone.now()
        self.activity.save(
            update_fields=[
                "status",
                "published_by",
                "published_at",
                "updated_at",
            ]
        )

    def publish_announcement(self):
        self.announcement.status = Announcement.Status.PUBLISHED
        self.announcement.published_by = self.pastor
        self.announcement.published_at = timezone.now()
        self.announcement.save(
            update_fields=[
                "status",
                "published_by",
                "published_at",
                "updated_at",
            ]
        )


class TestMediaUploadAPI(MediaAPITestCase):

    def test_pastor_can_upload_activity_media(self):
        response = self.upload_media(self.activity_media_url)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContentMedia.objects.count(), 1)
        self.assertEqual(response.data["category"], "IMAGE")

    def test_administrator_can_upload_announcement_media(self):
        response = self.upload_media(
            self.announcement_media_url,
            self.admin,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContentMedia.objects.count(), 1)

    def test_anonymous_user_cannot_upload_media(self):
        response = self.client.post(
            self.activity_media_url,
            {"file": self.create_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_zone_leader_cannot_upload_media(self):
        response = self.upload_media(
            self.activity_media_url,
            self.zone_leader,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_upload_to_published_content_is_rejected(self):
        self.publish_activity()

        response = self.upload_media(self.activity_media_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContentMedia.objects.count(), 0)

    def test_upload_to_missing_activity_returns_404(self):
        url = "/api/v1/activities/manage/" "00000000-0000-0000-0000-000000000001/media/"

        response = self.upload_media(url)

        self.assertEqual(response.status_code, 404)


class TestMediaManagementAPI(MediaAPITestCase):

    def test_pastor_can_list_activity_media(self):
        upload_response = self.upload_media(self.activity_media_url)
        self.assertEqual(upload_response.status_code, 201)

        response = self.client.get(self.activity_media_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_anonymous_user_cannot_list_management_media(self):
        response = self.client.get(self.activity_media_url)

        self.assertEqual(response.status_code, 401)

    def test_zone_leader_cannot_list_management_media(self):
        self.client.force_authenticate(user=self.zone_leader)

        response = self.client.get(self.activity_media_url)

        self.assertEqual(response.status_code, 403)

    def test_pastor_can_delete_draft_media(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.pastor)
        response = self.client.delete(f"/api/v1/media/manage/{media_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ContentMedia.objects.filter(pk=media_id).exists())

    def test_zone_leader_cannot_delete_media(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.zone_leader)
        response = self.client.delete(f"/api/v1/media/manage/{media_id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ContentMedia.objects.filter(pk=media_id).exists())

    def test_deleting_published_media_is_rejected(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]
        self.publish_activity()

        self.client.force_authenticate(user=self.pastor)
        response = self.client.delete(f"/api/v1/media/manage/{media_id}/")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(ContentMedia.objects.filter(pk=media_id).exists())

    def test_deleting_missing_media_returns_404(self):
        self.client.force_authenticate(user=self.pastor)

        response = self.client.delete(
            "/api/v1/media/manage/" "00000000-0000-0000-0000-000000000001/"
        )

        self.assertEqual(response.status_code, 404)


class TestMediaFileAccessAPI(MediaAPITestCase):

    def test_anonymous_user_cannot_access_draft_media(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/media/{media_id}/file/")

        self.assertEqual(response.status_code, 401)

    def test_zone_leader_cannot_access_draft_media(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.zone_leader)
        response = self.client.get(f"/api/v1/media/{media_id}/file/")

        self.assertEqual(response.status_code, 403)

    def test_pastor_can_access_draft_media(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.pastor)
        response = self.client.get(f"/api/v1/media/{media_id}/file/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(
            response["Cache-Control"],
            "private, no-store",
        )
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_published_activity_media_is_publicly_accessible(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]
        self.publish_activity()

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/media/{media_id}/file/")

        self.assertEqual(response.status_code, 200)

    def test_published_announcement_media_is_publicly_accessible(self):
        upload_response = self.upload_media(self.announcement_media_url)
        media_id = upload_response.data["id"]
        self.publish_announcement()

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/media/{media_id}/file/")

        self.assertEqual(response.status_code, 200)

    def test_archived_content_media_is_not_publicly_accessible(self):
        upload_response = self.upload_media(self.activity_media_url)
        media_id = upload_response.data["id"]

        self.activity.status = Activity.Status.ARCHIVED
        self.activity.save(update_fields=["status", "updated_at"])

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/media/{media_id}/file/")

        self.assertEqual(response.status_code, 401)

    def test_missing_media_file_returns_404(self):
        response = self.client.get(
            "/api/v1/media/" "00000000-0000-0000-0000-000000000001/file/"
        )

        self.assertEqual(response.status_code, 404)


class TestPublicContentMediaReferences(MediaAPITestCase):
    """Verify public content responses expose safe media references."""

    def assert_media_reference(self, media_data, media_id):
        self.assertEqual(len(media_data), 1)

        media = media_data[0]

        self.assertEqual(media["id"], str(media_id))
        self.assertEqual(media["category"], "IMAGE")
        self.assertEqual(media["original_filename"], "test-image.jpg")
        self.assertEqual(media["mime_type"], "image/jpeg")
        self.assertGreater(media["file_size"], 0)
        self.assertEqual(
            media["file_url"],
            f"/api/v1/media/{media_id}/file/",
        )

        self.assertNotIn("file", media)
        self.assertNotIn("uploaded_by", media)

    def test_public_activity_list_includes_media_references(self):
        upload_response = self.upload_media(self.activity_media_url)
        self.assertEqual(upload_response.status_code, 201)

        media_id = upload_response.data["id"]
        self.publish_activity()

        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/activities/")

        self.assertEqual(response.status_code, 200)

        activity_data = next(
            item for item in response.data if item["id"] == str(self.activity.id)
        )

        self.assert_media_reference(activity_data["media"], media_id)

    def test_public_activity_detail_includes_media_references(self):
        upload_response = self.upload_media(self.activity_media_url)
        self.assertEqual(upload_response.status_code, 201)

        media_id = upload_response.data["id"]
        self.publish_activity()

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/activities/public/{self.activity.id}/")

        self.assertEqual(response.status_code, 200)
        self.assert_media_reference(response.data["media"], media_id)

    def test_public_announcement_list_includes_media_references(self):
        upload_response = self.upload_media(self.announcement_media_url)
        self.assertEqual(upload_response.status_code, 201)

        media_id = upload_response.data["id"]
        self.publish_announcement()

        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/announcements/")

        self.assertEqual(response.status_code, 200)

        announcement_data = next(
            item
            for item in response.data["results"]
            if item["id"] == str(self.announcement.id)
        )

        self.assert_media_reference(announcement_data["media"], media_id)

    def test_public_announcement_detail_includes_media_references(self):
        upload_response = self.upload_media(self.announcement_media_url)
        self.assertEqual(upload_response.status_code, 201)

        media_id = upload_response.data["id"]
        self.publish_announcement()

        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/api/v1/announcements/public/{self.announcement.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assert_media_reference(response.data["media"], media_id)

    def test_draft_content_media_is_not_exposed_publicly(self):
        activity_upload = self.upload_media(self.activity_media_url)
        self.assertEqual(activity_upload.status_code, 201)

        announcement_upload = self.upload_media(self.announcement_media_url)
        self.assertEqual(announcement_upload.status_code, 201)

        self.client.force_authenticate(user=None)

        activity_response = self.client.get("/api/v1/activities/")
        announcement_response = self.client.get("/api/v1/announcements/")

        self.assertEqual(activity_response.status_code, 200)
        self.assertEqual(announcement_response.status_code, 200)

        self.assertFalse(
            any(item["id"] == str(self.activity.id) for item in activity_response.data)
        )

        self.assertFalse(
            any(
                item["id"] == str(self.announcement.id)
                for item in announcement_response.data["results"]
            )
        )
