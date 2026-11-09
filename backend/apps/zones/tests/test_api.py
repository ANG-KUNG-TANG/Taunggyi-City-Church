from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.zones.models.zones import Zone, ZoneLeaderAssignment
from apps.zones.services.zone_service import assign_zone_leader


ZONE_URL = "/api/v1/zones/"


class ZoneAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.pastor = User.objects.create_user(
            email="pastor-api@example.com",
            password="test-password",
        )
        self.leader = User.objects.create_user(
            email="leader-api@example.com",
            password="test-password",
        )
        self.other_leader = User.objects.create_user(
            email="other-leader-api@example.com",
            password="test-password",
        )
        self.member = User.objects.create_user(
            email="member-api@example.com",
            password="test-password",
        )

        self.pastor_role = Role.objects.get(code="PASTOR")
        self.leader_role = Role.objects.get(code="ZONE_LEADER")

        UserRole.objects.create(
            user=self.pastor,
            role=self.pastor_role,
        )
        UserRole.objects.create(
            user=self.leader,
            role=self.leader_role,
        )
        UserRole.objects.create(
            user=self.other_leader,
            role=self.leader_role,
        )

        self.north_zone = Zone.objects.create(
            name="North API Zone",
            description="North zone",
        )
        self.south_zone = Zone.objects.create(
            name="South API Zone",
            description="South zone",
        )

        self.north_assignment = assign_zone_leader(
            zone=self.north_zone,
            user=self.leader,
            actor=self.pastor,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_pastor_can_list_all_zones(self):
        self.authenticate(self.pastor)

        response = self.client.get(ZONE_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_zone_leader_can_list_assigned_zones(self):
        self.authenticate(self.leader)

        response = self.client.get(ZONE_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            str(self.north_zone.id),
        )

    def test_user_without_zone_role_cannot_list_zones(self):
        self.authenticate(self.member)

        response = self.client.get(ZONE_URL)

        self.assertEqual(response.status_code, 403)

    def test_pastor_can_create_zone(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            ZONE_URL,
            {
                "name": "Central API Zone",
                "description": "Central community",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["name"],
            "Central API Zone",
        )
        self.assertTrue(Zone.objects.filter(name="Central API Zone").exists())

    def test_zone_leader_cannot_create_zone(self):
        self.authenticate(self.leader)

        response = self.client.post(
            ZONE_URL,
            {"name": "Unauthorized API Zone"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Zone.objects.filter(name="Unauthorized API Zone").exists())

    def test_zone_leader_can_retrieve_assigned_zone(self):
        self.authenticate(self.leader)

        response = self.client.get(f"{ZONE_URL}{self.north_zone.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["name"],
            self.north_zone.name,
        )

    def test_zone_leader_cannot_retrieve_unassigned_zone(self):
        self.authenticate(self.leader)

        response = self.client.get(f"{ZONE_URL}{self.south_zone.id}/")

        self.assertEqual(response.status_code, 404)

    def test_pastor_can_update_zone(self):
        self.authenticate(self.pastor)

        response = self.client.patch(
            f"{ZONE_URL}{self.north_zone.id}/",
            {
                "name": "Updated North API Zone",
                "description": "Updated description",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["name"],
            "Updated North API Zone",
        )

    def test_pastor_can_deactivate_zone(self):
        self.authenticate(self.pastor)

        response = self.client.post(f"{ZONE_URL}{self.north_zone.id}/deactivate/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])

        self.north_zone.refresh_from_db()
        self.assertFalse(self.north_zone.is_active)

    def test_pastor_can_assign_zone_leader(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            f"{ZONE_URL}{self.south_zone.id}/leaders/",
            {
                "user_id": str(self.other_leader.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["user"],
            self.other_leader.id,
        )
        self.assertEqual(
            response.data["zone"],
            self.south_zone.id,
        )

        self.assertTrue(
            ZoneLeaderAssignment.objects.filter(
                zone=self.south_zone,
                user=self.other_leader,
                effective_to__isnull=True,
            ).exists()
        )

    def test_zone_leader_cannot_assign_another_leader(self):
        self.authenticate(self.leader)

        response = self.client.post(
            f"{ZONE_URL}{self.south_zone.id}/leaders/",
            {
                "user_id": str(self.other_leader.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_pastor_can_list_zone_leader_assignments(self):
        self.authenticate(self.pastor)

        response = self.client.get(f"{ZONE_URL}{self.north_zone.id}/leaders/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["user_email"],
            self.leader.email,
        )

    def test_pastor_can_end_zone_leader_assignment(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            (
                f"{ZONE_URL}{self.north_zone.id}/leaders/"
                f"{self.north_assignment.id}/end/"
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.north_assignment.refresh_from_db()
        self.assertIsNotNone(self.north_assignment.effective_to)

    def test_pastor_can_update_zone_with_put(self):
        self.authenticate(self.pastor)

        response = self.client.put(
            f"{ZONE_URL}{self.north_zone.id}/",
            {
                "name": "Updated North API Zone",
                "description": "Updated description",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["name"],
            "Updated North API Zone",
        )
        self.assertEqual(
            response.data["description"],
            "Updated description",
        )

    def test_zone_leader_can_retrieve_deactivated_assigned_zone(self):
        self.north_zone.is_active = False
        self.north_zone.save(update_fields=["is_active"])

        self.authenticate(self.leader)

        response = self.client.get(f"{ZONE_URL}{self.north_zone.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])

    def test_zone_leader_cannot_retrieve_zone_after_assignment_ends(self):
        from django.utils import timezone

        self.north_assignment.effective_to = timezone.now()
        self.north_assignment.save(update_fields=["effective_to"])

        self.authenticate(self.leader)

        response = self.client.get(f"{ZONE_URL}{self.north_zone.id}/")

        self.assertEqual(response.status_code, 404)

    def test_pastor_put_requires_complete_zone_data(self):
        self.authenticate(self.pastor)

        response = self.client.put(
            f"{ZONE_URL}{self.north_zone.id}/",
            {
                "name": "Updated North API Zone",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_user_cannot_list_zones(self):
        response = self.client.get(ZONE_URL)

        self.assertIn(response.status_code, [401, 403])
