from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.accounts.permissions.role_permission import (
    IsAdministrator,
    IsPastor,
    IsPastorOrAdministrator,
    IsZoneLeader,
)


class RolePermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="leader@example.com",
            password="test-password",
        )

        # Reuse roles created by the existing migration.
        self.zone_leader = Role.objects.get(code="ZONE_LEADER")

        self.pastor = Role.objects.get(code="PASTOR")

        self.administrator = Role.objects.get(code="ADMINISTRATOR")

        self.request = SimpleNamespace(user=self.user)
        self.view = SimpleNamespace()

    def assign_role(self, role):
        return UserRole.objects.create(
            user=self.user,
            role=role,
        )

    def test_unauthenticated_user_is_denied(self):
        self.request.user = AnonymousUser()

        permission = IsZoneLeader()

        self.assertFalse(permission.has_permission(self.request, self.view))

    def test_user_without_role_is_denied(self):
        permission = IsZoneLeader()

        self.assertFalse(permission.has_permission(self.request, self.view))

    def test_active_zone_leader_is_allowed(self):
        self.assign_role(self.zone_leader)

        permission = IsZoneLeader()

        self.assertTrue(permission.has_permission(self.request, self.view))

    def test_revoked_role_is_denied(self):
        assignment = self.assign_role(self.zone_leader)

        assignment.revoked_at = assignment.assigned_at
        assignment.save(update_fields=["revoked_at"])

        permission = IsZoneLeader()

        self.assertFalse(permission.has_permission(self.request, self.view))

    def test_zone_leader_cannot_access_pastor_permission(self):
        self.assign_role(self.zone_leader)

        permission = IsPastor()

        self.assertFalse(permission.has_permission(self.request, self.view))

    def test_pastor_is_allowed(self):
        self.assign_role(self.pastor)

        permission = IsPastor()

        self.assertTrue(permission.has_permission(self.request, self.view))

    def test_administrator_is_allowed(self):
        self.assign_role(self.administrator)

        permission = IsAdministrator()

        self.assertTrue(permission.has_permission(self.request, self.view))

    def test_pastor_or_administrator_accepts_pastor(self):
        self.assign_role(self.pastor)

        permission = IsPastorOrAdministrator()

        self.assertTrue(permission.has_permission(self.request, self.view))

    def test_pastor_or_administrator_accepts_administrator(self):
        self.assign_role(self.administrator)

        permission = IsPastorOrAdministrator()

        self.assertTrue(permission.has_permission(self.request, self.view))

    def test_inactive_user_is_denied(self):
        self.assign_role(self.zone_leader)

        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        permission = IsZoneLeader()

        self.assertFalse(permission.has_permission(self.request, self.view))
