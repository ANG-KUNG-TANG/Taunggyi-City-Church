from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase
from unittest.mock import patch

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.accounts.services import account_service
from apps.audit.models.audit_log import AuditLog
from apps.audit.services.audit_service import AuditService


class AccountServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrator_role = Role.objects.get(code="ADMINISTRATOR")
        cls.pastor_role = Role.objects.get(code="PASTOR")
        cls.zone_leader_role = Role.objects.get(code="ZONE_LEADER")

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="test-password",
        )
        self.assign_role(self.admin, self.administrator_role)

    @staticmethod
    def assign_role(user, role):
        return UserRole.objects.create(user=user, role=role)

    @staticmethod
    def create_user(email, password="test-password"):
        return User.objects.create_user(email=email, password=password)

    def test_anonymous_actor_is_denied(self):
        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(PermissionDenied):
            account_service.list_staff_accounts(actor=AnonymousUser())

    def test_inactive_administrator_is_denied(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            account_service.list_staff_accounts(actor=self.admin)

    def test_zone_leader_is_denied(self):
        leader = self.create_user("leader@example.com")
        self.assign_role(leader, self.zone_leader_role)

        with self.assertRaises(PermissionDenied):
            account_service.list_staff_accounts(actor=leader)

    def test_revoked_administrator_is_denied(self):
        assignment = self.admin.role_assignments.get(role=self.administrator_role)
        assignment.revoked_at = assignment.assigned_at
        assignment.save(update_fields=["revoked_at"])

        with self.assertRaises(PermissionDenied):
            account_service.list_staff_accounts(actor=self.admin)

    def test_create_account_uses_unusable_password_and_records_audit(self):
        account = account_service.create_staff_account(
            actor=self.admin,
            validated_data={
                "email": "new-staff@example.com",
                "first_name": "New",
                "last_name": "Staff",
            },
        )

        self.assertFalse(account.has_usable_password())

        event = AuditLog.objects.get(
            entity_type="StaffAccount",
            entity_id=account.pk,
            action=AuditLog.Action.CREATE,
        )
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(
            event.after_data,
            {
                "email": "new-staff@example.com",
                "first_name": "New",
                "last_name": "Staff",
                "is_active": True,
            },
        )
        self.assertNotIn("password", event.after_data)

    def test_create_rejects_privileged_fields(self):
        with self.assertRaises(ValidationError):
            account_service.create_staff_account(
                actor=self.admin,
                validated_data={
                    "email": "privileged@example.com",
                    "is_active": False,
                },
            )

        self.assertFalse(User.objects.filter(email="privileged@example.com").exists())

    def test_administrator_can_list_staff_accounts(self):
        staff = self.create_user("staff@example.com")

        accounts = account_service.list_staff_accounts(actor=self.admin)

        self.assertIn(staff, accounts)
        self.assertIn(self.admin, accounts)

    def test_administrator_can_retrieve_staff_account(self):
        staff = self.create_user("staff@example.com")

        result = account_service.get_staff_account(
            actor=self.admin,
            user_id=staff.pk,
        )

        self.assertEqual(result.pk, staff.pk)

    def test_update_changes_permitted_fields_and_records_safe_snapshots(self):
        staff = self.create_user("staff@example.com")

        updated = account_service.update_staff_account(
            actor=self.admin,
            user_id=staff.pk,
            changes={
                "first_name": "Updated",
                "last_name": "Member",
            },
        )

        self.assertEqual(updated.first_name, "Updated")
        self.assertEqual(updated.last_name, "Member")

        event = AuditLog.objects.get(
            entity_type="StaffAccount",
            entity_id=staff.pk,
            action=AuditLog.Action.UPDATE,
        )
        self.assertEqual(
            event.before_data,
            {
                "email": "staff@example.com",
                "first_name": "",
                "last_name": "",
                "is_active": True,
            },
        )
        self.assertEqual(
            event.after_data,
            {
                "email": "staff@example.com",
                "first_name": "Updated",
                "last_name": "Member",
                "is_active": True,
            },
        )

    def test_update_rejects_privileged_fields(self):
        staff = self.create_user("staff@example.com")

        for changes in (
            {"is_active": False},
            {"password": "new-password"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValidationError):
                    account_service.update_staff_account(
                        actor=self.admin,
                        user_id=staff.pk,
                        changes=changes,
                    )

        staff.refresh_from_db()
        self.assertTrue(staff.is_active)
        self.assertFalse(staff.has_usable_password() is False)

    def test_update_rejects_empty_changes(self):
        staff = self.create_user("staff@example.com")

        with self.assertRaises(ValidationError):
            account_service.update_staff_account(
                actor=self.admin,
                user_id=staff.pk,
                changes={},
            )

    def test_administrator_cannot_deactivate_themselves(self):
        with self.assertRaises(PermissionDenied):
            account_service.deactivate_staff_account(
                actor=self.admin,
                user_id=self.admin.pk,
            )

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_only_active_administrator_can_deactivate_staff_account(self):
        staff = self.create_user("staff@example.com")

        result = account_service.deactivate_staff_account(
            actor=self.admin,
            user_id=staff.pk,
        )

        result.refresh_from_db()
        self.admin.refresh_from_db()

        self.assertFalse(result.is_active)
        self.assertTrue(self.admin.is_active)

    def test_administrator_can_deactivate_another_administrator(self):
        other_admin = self.create_user("other-admin@example.com")
        self.assign_role(other_admin, self.administrator_role)

        result = account_service.deactivate_staff_account(
            actor=self.admin,
            user_id=other_admin.pk,
        )

        result.refresh_from_db()
        self.admin.refresh_from_db()

        self.assertFalse(result.is_active)
        self.assertTrue(self.admin.is_active)

        event = AuditLog.objects.get(
            entity_type="StaffAccount",
            entity_id=other_admin.pk,
            action=AuditLog.Action.UPDATE,
        )
        self.assertTrue(event.before_data["is_active"])
        self.assertFalse(event.after_data["is_active"])

    def test_audit_failure_rolls_back_account_creation(self):
        initial_count = User.objects.count()

        with patch.object(
            AuditService,
            "record_event",
            side_effect=RuntimeError("Audit service unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                account_service.create_staff_account(
                    actor=self.admin,
                    validated_data={"email": "rollback@example.com"},
                )

        self.assertEqual(User.objects.count(), initial_count)
        self.assertFalse(User.objects.filter(email="rollback@example.com").exists())

    def test_audit_failure_rolls_back_account_update(self):
        staff = self.create_user("staff@example.com")

        with patch.object(
            AuditService,
            "record_event",
            side_effect=RuntimeError("Audit service unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                account_service.update_staff_account(
                    actor=self.admin,
                    user_id=staff.pk,
                    changes={"first_name": "Changed"},
                )

        staff.refresh_from_db()
        self.assertEqual(staff.first_name, "")

    def test_audit_failure_rolls_back_deactivation(self):
        staff = self.create_user("staff@example.com")

        with patch.object(
            AuditService,
            "record_event",
            side_effect=RuntimeError("Audit service unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                account_service.deactivate_staff_account(
                    actor=self.admin,
                    user_id=staff.pk,
                )

        staff.refresh_from_db()
        self.assertTrue(staff.is_active)


class AccountDeactivationConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_simultaneous_administrator_deactivations_preserve_one_active_admin(
        self,
    ):
        if connection.vendor != "postgresql":
            self.skipTest("This concurrency test requires PostgreSQL.")

        administrator_role = Role.objects.get(code="ADMINISTRATOR")

        first_admin = User.objects.create_user(
            email="first-admin@example.com",
            password="test-password",
        )
        second_admin = User.objects.create_user(
            email="second-admin@example.com",
            password="test-password",
        )

        UserRole.objects.create(user=first_admin, role=administrator_role)
        UserRole.objects.create(user=second_admin, role=administrator_role)

        barrier = Barrier(2)
        original_check = account_service._require_administrator

        def synchronized_authorization(actor):
            original_check(actor)
            barrier.wait(timeout=15)

        def deactivate(actor_id, target_id):
            close_old_connections()
            try:
                actor = User.objects.get(pk=actor_id)
                account_service.deactivate_staff_account(
                    actor=actor,
                    user_id=target_id,
                )
                return "success"
            except (PermissionDenied, ValidationError):
                return "denied"
            finally:
                connections.close_all()

        with patch.object(
            account_service,
            "_require_administrator",
            side_effect=synchronized_authorization,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first_result = executor.submit(
                    deactivate,
                    first_admin.pk,
                    second_admin.pk,
                )
                second_result = executor.submit(
                    deactivate,
                    second_admin.pk,
                    first_admin.pk,
                )

                results = [
                    first_result.result(timeout=30),
                    second_result.result(timeout=30),
                ]

        self.assertIn("success", results)

        active_administrators = User.objects.filter(
            is_active=True,
            role_assignments__role=administrator_role,
            role_assignments__revoked_at__isnull=True,
        ).distinct()

        self.assertGreaterEqual(active_administrators.count(), 1)
