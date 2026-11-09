from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.members.models import Member
from apps.members.selectors.member_selector import get_members_for_user
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class MemberSelectorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pastor_role = Role.objects.get(code="PASTOR")
        cls.zone_leader_role = Role.objects.get(code="ZONE_LEADER")
        cls.admin_role = Role.objects.get(code="ADMINISTRATOR")

        cls.pastor = User.objects.create_user(
            email="pastor-selector@example.com",
            password="test-password",
        )

        cls.zone_leader = User.objects.create_user(
            email="leader-selector@example.com",
            password="test-password",
        )

        cls.other_user = User.objects.create_user(
            email="other-selector@example.com",
            password="test-password",
        )

        cls.inactive_user = User.objects.create_user(
            email="inactive-selector@example.com",
            password="test-password",
        )
        cls.inactive_user.is_active = False
        cls.inactive_user.save(update_fields=["is_active"])

        UserRole.objects.create(
            user=cls.pastor,
            role=cls.pastor_role,
        )

        UserRole.objects.create(
            user=cls.zone_leader,
            role=cls.zone_leader_role,
        )

        UserRole.objects.create(
            user=cls.other_user,
            role=cls.admin_role,
        )

        cls.zone_a = Zone.objects.create(
            name="Selector Zone A",
        )

        cls.zone_b = Zone.objects.create(
            name="Selector Zone B",
        )

        cls.inactive_zone = Zone.objects.create(
            name="Selector Inactive Zone",
            is_active=False,
        )

        cls.member_a = Member.objects.create(
            zone=cls.zone_a,
            full_name="Alice Johnson",
            phone="0912345678",
            created_by=cls.pastor,
        )

        cls.member_b = Member.objects.create(
            zone=cls.zone_b,
            full_name="Benjamin Smith",
            phone="0923456789",
            created_by=cls.pastor,
        )

        cls.member_inactive_zone = Member.objects.create(
            zone=cls.inactive_zone,
            full_name="Inactive Zone Member",
            phone="0934567890",
            created_by=cls.pastor,
        )

        now = timezone.now()

        cls.current_assignment = ZoneLeaderAssignment.objects.create(
            zone=cls.zone_a,
            user=cls.zone_leader,
            assigned_by=cls.pastor,
            effective_from=now - timedelta(days=1),
        )

    def test_pastor_can_access_members_in_all_active_zones(self):
        members = get_members_for_user(self.pastor)

        self.assertIn(self.member_a, members)
        self.assertIn(self.member_b, members)
        self.assertNotIn(self.member_inactive_zone, members)

    def test_zone_leader_can_access_assigned_zone_members(self):
        members = get_members_for_user(self.zone_leader)

        self.assertIn(self.member_a, members)
        self.assertNotIn(self.member_b, members)

    def test_zone_leader_cannot_access_unassigned_zone(self):
        members = get_members_for_user(
            self.zone_leader,
            zone_id=self.zone_b.id,
        )

        self.assertFalse(members.exists())

    def test_zone_leader_can_filter_to_assigned_zone(self):
        members = get_members_for_user(
            self.zone_leader,
            zone_id=self.zone_a.id,
        )

        self.assertIn(self.member_a, members)
        self.assertNotIn(self.member_b, members)

    def test_expired_assignment_does_not_grant_access(self):
        self.current_assignment.effective_to = timezone.now() - timedelta(days=1)
        self.current_assignment.save(update_fields=["effective_to"])

        members = get_members_for_user(self.zone_leader)

        self.assertFalse(members.exists())

    def test_future_assignment_does_not_grant_access(self):
        self.current_assignment.effective_from = timezone.now() + timedelta(days=1)
        self.current_assignment.save(update_fields=["effective_from"])

        members = get_members_for_user(self.zone_leader)

        self.assertFalse(members.exists())

    def test_revoked_role_does_not_grant_access(self):
        UserRole.objects.filter(
            user=self.zone_leader,
            role=self.zone_leader_role,
        ).update(revoked_at=timezone.now())

        members = get_members_for_user(self.zone_leader)

        self.assertFalse(members.exists())

    def test_inactive_user_cannot_access_members(self):
        members = get_members_for_user(self.inactive_user)

        self.assertFalse(members.exists())

    def test_administrator_has_no_implicit_member_access(self):
        members = get_members_for_user(self.other_user)

        self.assertFalse(members.exists())

    def test_search_matches_member_name(self):
        members = get_members_for_user(
            self.pastor,
            search="Alice",
        )

        self.assertIn(self.member_a, members)
        self.assertNotIn(self.member_b, members)

    def test_search_matches_member_phone(self):
        members = get_members_for_user(
            self.pastor,
            search="092345",
        )

        self.assertIn(self.member_b, members)
        self.assertNotIn(self.member_a, members)

    def test_search_is_trimmed(self):
        members = get_members_for_user(
            self.pastor,
            search="  Alice  ",
        )

        self.assertIn(self.member_a, members)
        self.assertNotIn(self.member_b, members)

    def test_anonymous_user_cannot_access_members(self):
        from django.contrib.auth.models import AnonymousUser

        members = get_members_for_user(AnonymousUser())

        self.assertFalse(members.exists())
