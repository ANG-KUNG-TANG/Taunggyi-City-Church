from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.members.models import Member
from apps.members.services.member_service import create_member
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class MemberAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.pastor = self.create_user("pastor@example.com")
        self.leader = self.create_user("leader@example.com")
        self.other_leader = self.create_user("other-leader@example.com")
        self.ordinary_user = self.create_user("ordinary@example.com")
        self.administrator = self.create_user("admin@example.com")

        self.pastor_role = Role.objects.get(code="PASTOR")
        self.leader_role = Role.objects.get(code="ZONE_LEADER")
        self.administrator_role = Role.objects.get(code="ADMINISTRATOR")

        self.assign_role(self.pastor, self.pastor_role)
        self.assign_role(self.leader, self.leader_role)
        self.assign_role(self.other_leader, self.leader_role)
        self.assign_role(
            self.administrator,
            self.administrator_role,
        )

        self.zone = Zone.objects.create(name="Zone A")
        self.other_zone = Zone.objects.create(name="Zone B")

        self.assign_zone_leader(self.leader, self.zone)
        self.assign_zone_leader(
            self.other_leader,
            self.other_zone,
        )

        self.list_url = reverse("members:member-list-create")

    def create_user(self, email):
        return User.objects.create_user(
            email=email,
            password="test-password",
        )

    def assign_role(self, user, role):
        return UserRole.objects.create(
            user=user,
            role=role,
        )

    def assign_zone_leader(self, user, zone):
        return ZoneLeaderAssignment.objects.create(
            zone=zone,
            user=user,
            assigned_by=self.pastor,
            effective_from=timezone.now() - timedelta(minutes=1),
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_member(self, *, actor=None, zone=None, name="Test Member"):
        return create_member(
            zone=zone or self.zone,
            full_name=name,
            actor=actor or self.pastor,
        )

    def detail_url(self, member):
        return reverse(
            "members:member-detail",
            kwargs={"member_id": member.id},
        )

    def transfer_url(self, member):
        return reverse(
            "members:member-transfer",
            kwargs={"member_id": member.id},
        )

    # Authentication and role restrictions

    def test_unauthenticated_user_cannot_list_members(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_ordinary_user_cannot_list_members(self):
        self.authenticate(self.ordinary_user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_administrator_cannot_list_members(self):
        self.authenticate(self.administrator)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    # Member listing and zone filtering

    def test_pastor_can_list_members_across_active_zones(self):
        member_a = self.create_member(zone=self.zone)
        member_b = self.create_member(
            zone=self.other_zone,
            name="Another Member",
        )

        self.authenticate(self.pastor)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        returned_ids = {item["id"] for item in response.data["results"]}

        self.assertEqual(
            returned_ids,
            {str(member_a.id), str(member_b.id)},
        )

    def test_zone_leader_only_sees_assigned_zone_members(self):
        own_member = self.create_member(zone=self.zone)
        self.create_member(
            zone=self.other_zone,
            name="Other Zone Member",
        )

        self.authenticate(self.leader)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

        returned_ids = {item["id"] for item in response.data["results"]}

        self.assertEqual(returned_ids, {str(own_member.id)})

    def test_zone_leader_can_filter_by_assigned_zone(self):
        own_member = self.create_member(zone=self.zone)

        self.authenticate(self.leader)

        response = self.client.get(
            self.list_url,
            {"zone_id": str(self.zone.id)},
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = {item["id"] for item in response.data["results"]}

        self.assertEqual(returned_ids, {str(own_member.id)})

    # Member creation

    def test_pastor_can_create_member(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            self.list_url,
            {
                "zone_id": str(self.other_zone.id),
                "full_name": "New Member",
                "phone": "0912345678",
                "address": "Taunggyi",
                "notes": "API test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        member = Member.objects.get(id=response.data["id"])

        self.assertEqual(member.full_name, "New Member")
        self.assertEqual(member.zone, self.other_zone)
        self.assertEqual(member.created_by, self.pastor)

    def test_zone_leader_can_create_member_in_assigned_zone(self):
        self.authenticate(self.leader)

        response = self.client.post(
            self.list_url,
            {
                "zone_id": str(self.zone.id),
                "full_name": "Zone Member",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        member = Member.objects.get(id=response.data["id"])

        self.assertEqual(member.zone, self.zone)
        self.assertEqual(member.created_by, self.leader)

    def test_zone_leader_cannot_create_member_in_unassigned_zone(self):
        self.authenticate(self.leader)

        response = self.client.post(
            self.list_url,
            {
                "zone_id": str(self.other_zone.id),
                "full_name": "Unauthorized Member",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Member.objects.filter(full_name="Unauthorized Member").exists()
        )

    def test_member_creation_rejects_empty_name(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            self.list_url,
            {
                "zone_id": str(self.zone.id),
                "full_name": "   ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_member_creation_rejects_client_controlled_fields(self):
        self.authenticate(self.pastor)

        response = self.client.post(
            self.list_url,
            {
                "zone_id": str(self.zone.id),
                "full_name": "Invalid Member",
                "created_by": str(self.pastor.id),
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    # Member retrieval

    def test_pastor_can_retrieve_member(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.get(self.detail_url(member))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(member.id))

    def test_zone_leader_can_retrieve_member_in_assigned_zone(self):
        member = self.create_member()

        self.authenticate(self.leader)

        response = self.client.get(self.detail_url(member))

        self.assertEqual(response.status_code, 200)

    def test_zone_leader_cannot_retrieve_member_in_another_zone(self):
        member = self.create_member(zone=self.other_zone)

        self.authenticate(self.leader)

        response = self.client.get(self.detail_url(member))

        self.assertEqual(response.status_code, 404)

    # Member updates and version conflicts

    def test_pastor_can_update_member(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.patch(
            self.detail_url(member),
            {
                "full_name": "Updated Member",
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        member.refresh_from_db()

        self.assertEqual(member.full_name, "Updated Member")
        self.assertEqual(member.version, 2)

    def test_zone_leader_can_update_member_in_assigned_zone(self):
        member = self.create_member()

        self.authenticate(self.leader)

        response = self.client.patch(
            self.detail_url(member),
            {
                "phone": "0912345678",
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        member.refresh_from_db()

        self.assertEqual(member.phone, "0912345678")

    def test_stale_member_version_returns_conflict(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.patch(
            self.detail_url(member),
            {
                "full_name": "Stale Update",
                "expected_version": member.version + 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)

        member.refresh_from_db()

        self.assertEqual(member.full_name, "Test Member")
        self.assertEqual(member.version, 1)

    def test_member_update_rejects_zone_change(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.patch(
            self.detail_url(member),
            {
                "zone_id": str(self.other_zone.id),
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)

    # Member transfers

    def test_pastor_can_transfer_member(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.post(
            self.transfer_url(member),
            {
                "destination_zone_id": str(self.other_zone.id),
                "reason": "Approved member relocation",
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        member.refresh_from_db()

        self.assertEqual(member.zone, self.other_zone)
        self.assertEqual(member.version, 2)
        self.assertEqual(member.updated_by, self.pastor)

    def test_zone_leader_cannot_transfer_member(self):
        member = self.create_member()

        self.authenticate(self.leader)

        response = self.client.post(
            self.transfer_url(member),
            {
                "destination_zone_id": str(self.other_zone.id),
                "reason": "Unauthorized transfer",
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertEqual(member.version, 1)

    def test_administrator_cannot_transfer_member(self):
        member = self.create_member()

        self.authenticate(self.administrator)

        response = self.client.post(
            self.transfer_url(member),
            {
                "destination_zone_id": str(self.other_zone.id),
                "reason": "Administrator transfer",
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)

    def test_transfer_rejects_blank_reason(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.post(
            self.transfer_url(member),
            {
                "destination_zone_id": str(self.other_zone.id),
                "reason": "   ",
                "expected_version": member.version,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)

    def test_transfer_rejects_stale_version(self):
        member = self.create_member()

        self.authenticate(self.pastor)

        response = self.client.post(
            self.transfer_url(member),
            {
                "destination_zone_id": str(self.other_zone.id),
                "reason": "Approved relocation",
                "expected_version": member.version + 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertEqual(member.version, 1)
