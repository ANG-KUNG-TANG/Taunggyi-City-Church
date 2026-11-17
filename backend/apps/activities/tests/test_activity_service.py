"""
Direct service-level authorisation tests for ActivityService.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.activities.models.activity import Activity
from apps.activities.services.activities_services import ActivityService
from apps.audit.models.audit_log import AuditLog


class ActivityServiceAuthorizationTests(TestCase):
    """Verify service-level role enforcement and side-effect prevention."""

    def setUp(self):
        self.activity = Activity.objects.create(
            title="Sunday Worship",
            body="Join us for Sunday worship.",
            status=Activity.Status.DRAFT,
        )

    def create_user_with_role(self, email, role_code, role_name):
        user = User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

        role, _ = Role.objects.get_or_create(
            code=role_code,
            defaults={"name": role_name},
        )

        assignment = UserRole.objects.create(
            user=user,
            role=role,
        )

        return user, assignment

    def invoke_all_operations(self, actor):
        """Attempt every mutating operation with the supplied actor."""
        operations = [
            (
                "create",
                lambda: ActivityService.create_activity(
                    actor=actor,
                    title="New Activity",
                    body="Activity description.",
                ),
            ),
            (
                "update",
                lambda: ActivityService.update_activity(
                    actor=actor,
                    activity_id=self.activity.id,
                    title="Updated Activity",
                    body="Updated description.",
                ),
            ),
            (
                "publish",
                lambda: ActivityService.publish_activity(
                    actor=actor,
                    activity_id=self.activity.id,
                ),
            ),
            (
                "archive",
                lambda: ActivityService.archive_activity(
                    actor=actor,
                    activity_id=self.activity.id,
                ),
            ),
        ]

        initial_activity_count = Activity.objects.count()
        initial_audit_count = AuditLog.objects.count()

        for operation_name, operation in operations:
            with self.subTest(operation=operation_name):
                with self.assertRaises(PermissionDenied):
                    operation()

                self.activity.refresh_from_db()

                self.assertEqual(
                    Activity.objects.count(),
                    initial_activity_count,
                )
                self.assertEqual(
                    AuditLog.objects.count(),
                    initial_audit_count,
                )
                self.assertEqual(
                    self.activity.title,
                    "Sunday Worship",
                )
                self.assertEqual(
                    self.activity.body,
                    "Join us for Sunday worship.",
                )
                self.assertEqual(
                    self.activity.status,
                    Activity.Status.DRAFT,
                )

    def test_anonymous_actor_is_rejected_by_all_operations(self):
        self.invoke_all_operations(None)

    def test_inactive_user_is_rejected_by_all_operations(self):
        user, _ = self.create_user_with_role(
            "inactive@example.com",
            "PASTOR",
            "Pastor",
        )
        user.is_active = False
        user.save(update_fields=["is_active"])

        self.invoke_all_operations(user)

    def test_zone_leader_is_rejected_by_all_operations(self):
        user, _ = self.create_user_with_role(
            "zoneleader@example.com",
            "ZONE_LEADER",
            "Zone Leader",
        )

        self.invoke_all_operations(user)

    def test_revoked_manager_assignment_is_rejected(self):
        user, assignment = self.create_user_with_role(
            "revoked@example.com",
            "PASTOR",
            "Pastor",
        )
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])

        self.invoke_all_operations(user)

    def test_pastor_and_administrator_can_use_all_operations(self):
        managers = [
            ("pastor@example.com", "PASTOR", "Pastor"),
            (
                "admin@example.com",
                "ADMINISTRATOR",
                "Administrator",
            ),
        ]

        for email, role_code, role_name in managers:
            with self.subTest(role=role_code):
                user, _ = self.create_user_with_role(
                    email,
                    role_code,
                    role_name,
                )

                manager_activity = Activity.objects.create(
                    title=f"{role_name} Test Activity",
                    body="Activity for independent service testing.",
                    status=Activity.Status.DRAFT,
                )

                created_activity = ActivityService.create_activity(
                    actor=user,
                    title=f"{role_name} Activity",
                    body="Created through the service.",
                )

                updated_activity = ActivityService.update_activity(
                    actor=user,
                    activity_id=manager_activity.id,
                    title=f"Updated by {role_name}",
                    body="Updated through the service.",
                )

                published_activity = ActivityService.publish_activity(
                    actor=user,
                    activity_id=created_activity.id,
                )

                archived_activity = ActivityService.archive_activity(
                    actor=user,
                    activity_id=updated_activity.id,
                )

                self.assertEqual(
                    published_activity.status,
                    Activity.Status.PUBLISHED,
                )
                self.assertEqual(
                    archived_activity.status,
                    Activity.Status.ARCHIVED,
                )
                self.assertEqual(
                    AuditLog.objects.filter(actor=user).count(),
                    4,
                )
