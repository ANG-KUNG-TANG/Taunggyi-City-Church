from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIRequestFactory
from django.utils import timezone
from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.attendance.permissions.attendance_permissions import (
    IsAttendanceActor,
    IsAttendancePastor,
    IsAttendanceZoneLeader,
)


class AttendancePermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SimpleNamespace()

        self.pastor = self.create_user("pastor@example.com")
        self.leader = self.create_user("leader@example.com")
        self.ordinary_user = self.create_user("ordinary@example.com")
        self.admin = self.create_user("admin@example.com")

        self.pastor_role = Role.objects.get(code="PASTOR")
        self.leader_role = Role.objects.get(code="ZONE_LEADER")

        self.assign_role(self.pastor, self.pastor_role)
        self.assign_role(self.leader, self.leader_role)

        self.actor_permission = IsAttendanceActor()
        self.pastor_permission = IsAttendancePastor()
        self.leader_permission = IsAttendanceZoneLeader()

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

    def make_request(self, user):
        request = self.factory.get("/api/attendance/")
        request.user = user
        return request

    def test_pastor_can_access_attendance_actor_permission(self):
        request = self.make_request(self.pastor)

        self.assertTrue(self.actor_permission.has_permission(request, self.view))

    def test_zone_leader_can_access_attendance_actor_permission(self):
        request = self.make_request(self.leader)

        self.assertTrue(self.actor_permission.has_permission(request, self.view))

    def test_ordinary_user_is_denied_attendance_access(self):
        request = self.make_request(self.ordinary_user)

        self.assertFalse(self.actor_permission.has_permission(request, self.view))

    def test_admin_without_attendance_role_is_denied(self):
        request = self.make_request(self.admin)

        self.assertFalse(self.actor_permission.has_permission(request, self.view))

    def test_inactive_pastor_is_denied(self):
        self.pastor.is_active = False
        self.pastor.save(update_fields=["is_active"])

        request = self.make_request(self.pastor)

        self.assertFalse(self.actor_permission.has_permission(request, self.view))

    def test_revoked_pastor_role_does_not_grant_access(self):
        assignment = self.pastor.role_assignments.get(role=self.pastor_role)
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])

        request = self.make_request(self.pastor)

        self.assertFalse(self.actor_permission.has_permission(request, self.view))

    def test_pastor_permission_allows_pastor(self):
        request = self.make_request(self.pastor)

        self.assertTrue(self.pastor_permission.has_permission(request, self.view))

    def test_pastor_permission_rejects_zone_leader(self):
        request = self.make_request(self.leader)

        self.assertFalse(self.pastor_permission.has_permission(request, self.view))

    def test_zone_leader_permission_allows_zone_leader(self):
        request = self.make_request(self.leader)

        self.assertTrue(self.leader_permission.has_permission(request, self.view))

    def test_zone_leader_permission_rejects_pastor(self):
        request = self.make_request(self.pastor)

        self.assertFalse(self.leader_permission.has_permission(request, self.view))

    def test_inactive_zone_leader_is_rejected(self):
        self.leader.is_active = False
        self.leader.save(update_fields=["is_active"])

        request = self.make_request(self.leader)

        self.assertFalse(self.leader_permission.has_permission(request, self.view))

    def test_revoked_zone_leader_role_is_rejected(self):
        assignment = self.leader.role_assignments.get(role=self.leader_role)
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])

        request = self.make_request(self.leader)

        self.assertFalse(self.leader_permission.has_permission(request, self.view))

    def test_unauthenticated_user_is_rejected_by_all_permissions(self):
        request = self.make_request(None)

        self.assertFalse(self.actor_permission.has_permission(request, self.view))
        self.assertFalse(self.pastor_permission.has_permission(request, self.view))
        self.assertFalse(self.leader_permission.has_permission(request, self.view))
