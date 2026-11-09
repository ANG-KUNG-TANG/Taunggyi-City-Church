from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.members.models import Member
from apps.members.permissions.member_permission import CanAccessMembers
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class MemberPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pastor_role = Role.objects.get(code="PASTOR")
        cls.zone_leader_role = Role.objects.get(code="ZONE_LEADER")
        cls.admin_role = Role.objects.get(code="ADMINISTRATOR")

        cls.pastor = User.objects.create_user(
            email="pastor-permission@example.com",
            password="test-password",
        )
        cls.zone_leader = User.objects.create_user(
            email="leader-permission@example.com",
            password="test-password",
        )
        cls.admin = User.objects.create_user(
            email="admin-permission@example.com",
            password="test-password",
        )
        cls.inactive_user = User.objects.create_user(
            email="inactive-permission@example.com",
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
            user=cls.admin,
            role=cls.admin_role,
        )
        UserRole.objects.create(
            user=cls.inactive_user,
            role=cls.zone_leader_role,
        )

        cls.zone_a = Zone.objects.create(name="Permission Zone A")
        cls.zone_b = Zone.objects.create(name="Permission Zone B")

        cls.member_a = Member.objects.create(
            zone=cls.zone_a,
            full_name="Permission Member A",
            phone="0911111111",
            created_by=cls.pastor,
        )
        cls.member_b = Member.objects.create(
            zone=cls.zone_b,
            full_name="Permission Member B",
            phone="0922222222",
            created_by=cls.pastor,
        )

        now = timezone.now()

        ZoneLeaderAssignment.objects.create(
            zone=cls.zone_a,
            user=cls.zone_leader,
            assigned_by=cls.pastor,
            effective_from=now - timedelta(days=1),
        )

        ZoneLeaderAssignment.objects.create(
            zone=cls.zone_a,
            user=cls.inactive_user,
            assigned_by=cls.pastor,
            effective_from=now - timedelta(days=1),
        )

    def setUp(self):
        self.permission = CanAccessMembers()
        self.view = SimpleNamespace()

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def test_pastor_has_request_permission(self):
        request = self.request_for(self.pastor)

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_zone_leader_has_request_permission(self):
        request = self.request_for(self.zone_leader)

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_administrator_is_denied_request_permission(self):
        request = self.request_for(self.admin)

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_anonymous_user_is_denied(self):
        request = self.request_for(AnonymousUser())

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_inactive_user_is_denied(self):
        request = self.request_for(self.inactive_user)

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_pastor_can_access_member_in_any_zone(self):
        request = self.request_for(self.pastor)

        self.assertTrue(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_b,
            )
        )

    def test_zone_leader_can_access_member_in_assigned_zone(self):
        request = self.request_for(self.zone_leader)

        self.assertTrue(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_a,
            )
        )

    def test_zone_leader_cannot_access_member_in_unassigned_zone(self):
        request = self.request_for(self.zone_leader)

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_b,
            )
        )

    def test_administrator_cannot_access_member_object(self):
        request = self.request_for(self.admin)

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_a,
            )
        )

    def test_inactive_zone_leader_cannot_access_member_object(self):
        request = self.request_for(self.inactive_user)

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_a,
            )
        )

    def test_expired_assignment_does_not_grant_object_permission(self):
        now = timezone.now()

        ZoneLeaderAssignment.objects.filter(
            zone=self.zone_a,
            user=self.zone_leader,
        ).update(effective_to=now - timedelta(days=1))

        request = self.request_for(self.zone_leader)

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_a,
            )
        )

    def test_future_assignment_does_not_grant_object_permission(self):
        now = timezone.now()

        ZoneLeaderAssignment.objects.filter(
            zone=self.zone_a,
            user=self.zone_leader,
        ).update(effective_from=now + timedelta(days=1))

        request = self.request_for(self.zone_leader)

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_a,
            )
        )

    def test_revoked_zone_leader_role_denies_object_permission(self):
        UserRole.objects.filter(
            user=self.zone_leader,
            role=self.zone_leader_role,
        ).update(revoked_at=timezone.now())

        request = self.request_for(self.zone_leader)

        self.assertFalse(
            self.permission.has_object_permission(
                request,
                self.view,
                self.member_a,
            )
        )
