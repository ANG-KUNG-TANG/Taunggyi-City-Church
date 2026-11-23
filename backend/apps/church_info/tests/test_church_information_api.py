from django.test import TestCase
from rest_framework.test import APIClient

from apps.church_info.models.church_information import ChurchInformation


class PublicChurchInformationAPITestCase(TestCase):
    """Test public access to approved church information."""

    def setUp(self):
        self.client = APIClient()
        self.public_url = "/api/v1/public/church-info"

    def create_church_information(self, *, is_published):
        information = ChurchInformation.objects.create(
            church_name="Taunggyi City Church",
            description="A Christian church community in Taunggyi.",
            address="Taunggyi, Myanmar",
            phone="+959123456789",
            email="info@example.com",
            website="https://example.com",
            service_times=[
                {"day": "Sunday", "time": "09:00"},
            ],
            social_links=[
                {"platform": "Facebook", "url": "https://facebook.com/example"},
            ],
            is_published=is_published,
        )
        return information

    def test_anonymous_user_can_retrieve_published_information(self):
        self.create_church_information(is_published=True)

        response = self.client.get(self.public_url)

        self.assertEqual(
            response.status_code, 200, getattr(response, "data", response.content)
        )
        self.assertEqual(
            response.data["church_name"],
            "Taunggyi City Church",
        )

    def test_unpublished_information_is_not_publicly_accessible(self):
        self.create_church_information(is_published=False)

        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 404)

    def test_missing_church_information_returns_404(self):
        response = self.client.get(self.public_url)

        self.assertEqual(response.status_code, 404)

    def test_response_contains_only_approved_public_fields(self):
        self.create_church_information(is_published=True)

        response = self.client.get(self.public_url)

        expected_fields = {
            "church_name",
            "description",
            "address",
            "phone",
            "email",
            "website",
            "service_times",
            "social_links",
            "updated_at",
        }

        self.assertEqual(
            response.status_code, 200, getattr(response, "data", response.content)
        )
        self.assertEqual(set(response.data.keys()), expected_fields)
        self.assertNotIn("is_published", response.data)
        self.assertNotIn("member", response.data)
        self.assertNotIn("attendance", response.data)
        self.assertNotIn("finance", response.data)
