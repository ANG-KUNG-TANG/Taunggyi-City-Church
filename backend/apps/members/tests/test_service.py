from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.members.models import Member
from apps.members.services.member_service import (
    create_member,
    update_member,
)
from apps.zones.models.zones import (
    Zone,
    ZoneLeaderAssignment,
)


class MemberServiceTests(TestCase):
    def setUp(self):
        self.pastor = User.objects.create_user(
            email="pastor@example.com",
            password="test-password",
        )

        self.leader = User.objects.create_user(
            email="leader@example.com",
            password="test-password",
        )

        self.other_leader = User.objects.create_user(
            email="other-leader@example.com",
            password="test-password",
        )

        self.ordinary_user = User.objects.create_user(
            email="member-manager@example.com",
            password="test-password",
        )

        self.pastor_role = Role.objects.get(code="PASTOR")
        self.leader_role = Role.objects.get(code="ZONE_LEADER")

        self.assign_role(self.pastor, self.pastor_role)
        self.assign_role(self.leader, self.leader_role)
        self.assign_role(self.other_leader, self.leader_role)

        self.zone = Zone.objects.create(name="Zone A")
        self.other_zone = Zone.objects.create(name="Zone B")

        self.assign_zone_leader(
            user=self.leader,
            zone=self.zone,
        )

        self.assign_zone_leader(
            user=self.other_leader,
            zone=self.other_zone,
        )

    def assign_role(self, user, role):
        return UserRole.objects.create(
            user=user,
            role=role,
        )

    def assign_zone_leader(self, *, user, zone):
        return ZoneLeaderAssignment.objects.create(
            zone=zone,
            user=user,
            assigned_by=self.pastor,
            effective_from=timezone.now(),
        )

    def create_member(self, *, actor=None, zone=None):
        return create_member(
            zone=zone or self.zone,
            full_name="Test Member",
            actor=actor or self.pastor,
        )

    def test_pastor_can_create_member_in_any_active_zone(self):
        member = self.create_member(
            actor=self.pastor,
            zone=self.other_zone,
        )

        self.assertEqual(member.zone, self.other_zone)
        self.assertEqual(member.created_by, self.pastor)

        audit = AuditLog.objects.get(
            entity_type="Member",
            entity_id=member.id,
            action=AuditLog.Action.CREATE,
        )

        self.assertEqual(audit.actor, self.pastor)
        self.assertEqual(audit.after_data["full_name"], "Test Member")

    def test_zone_leader_can_create_member_in_assigned_zone(self):
        member = self.create_member(actor=self.leader)

        self.assertEqual(member.zone, self.zone)
        self.assertEqual(member.created_by, self.leader)

    def test_zone_leader_cannot_create_member_in_unassigned_zone(self):
        with self.assertRaises(ValidationError):
            self.create_member(
                actor=self.leader,
                zone=self.other_zone,
            )

        self.assertEqual(Member.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_user_without_member_role_cannot_create_member(self):
        with self.assertRaises(ValidationError):
            self.create_member(actor=self.ordinary_user)

        self.assertEqual(Member.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_inactive_user_cannot_create_member(self):
        self.pastor.is_active = False
        self.pastor.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            self.create_member(actor=self.pastor)

        self.assertEqual(Member.objects.count(), 0)

    def test_member_name_is_trimmed(self):
        member = create_member(
            zone=self.zone,
            full_name="  Test Member  ",
            actor=self.pastor,
        )

        self.assertEqual(member.full_name, "Test Member")

    def test_empty_member_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_member(
                zone=self.zone,
                full_name="   ",
                actor=self.pastor,
            )

        self.assertEqual(Member.objects.count(), 0)

    def test_member_creation_audit_failure_rolls_back_member(self):
        with patch(
            "apps.members.services.member_service." "AuditService.record_event",
            side_effect=RuntimeError("Audit failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.create_member(actor=self.pastor)

        self.assertEqual(Member.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_pastor_can_update_member(self):
        member = self.create_member()

        updated = update_member(
            member=member,
            actor=self.pastor,
            full_name="Updated Member",
            phone="0912345678",
        )

        updated.refresh_from_db()

        self.assertEqual(updated.full_name, "Updated Member")
        self.assertEqual(updated.phone, "0912345678")
        self.assertEqual(updated.updated_by, self.pastor)

        audit = AuditLog.objects.get(
            entity_type="Member",
            entity_id=member.id,
            action=AuditLog.Action.UPDATE,
        )

        self.assertEqual(audit.actor, self.pastor)
        self.assertEqual(audit.before_data["full_name"], "Test Member")
        self.assertEqual(audit.after_data["full_name"], "Updated Member")

    def test_zone_leader_can_update_member_in_assigned_zone(self):
        member = self.create_member()

        updated = update_member(
            member=member,
            actor=self.leader,
            phone="0912345678",
        )

        updated.refresh_from_db()

        self.assertEqual(updated.phone, "0912345678")
        self.assertEqual(updated.updated_by, self.leader)

    def test_zone_leader_cannot_update_member_in_unassigned_zone(self):
        member = self.create_member(
            actor=self.pastor,
            zone=self.other_zone,
        )

        with self.assertRaises(ValidationError):
            update_member(
                member=member,
                actor=self.leader,
                full_name="Unauthorized Update",
            )

        member.refresh_from_db()

        self.assertEqual(member.full_name, "Test Member")

        self.assertFalse(
            AuditLog.objects.filter(
                entity_type="Member",
                entity_id=member.id,
                action=AuditLog.Action.UPDATE,
            ).exists()
        )

    def test_update_without_changes_does_not_create_audit_event(self):
        member = self.create_member()

        audit_count = AuditLog.objects.count()

        updated = update_member(
            member=member,
            actor=self.pastor,
            full_name=member.full_name,
        )

        self.assertEqual(updated.full_name, member.full_name)
        self.assertEqual(AuditLog.objects.count(), audit_count)

    def test_empty_updated_name_is_rejected(self):
        member = self.create_member()

        with self.assertRaises(ValidationError):
            update_member(
                member=member,
                actor=self.pastor,
                full_name="   ",
            )

        member.refresh_from_db()

        self.assertEqual(member.full_name, "Test Member")

    def test_invalid_active_status_is_rejected(self):
        member = self.create_member()

        with self.assertRaises(ValidationError):
            update_member(
                member=member,
                actor=self.pastor,
                is_active="false",
            )

        member.refresh_from_db()

        self.assertTrue(member.is_active)

    def test_update_audit_failure_rolls_back_member_changes(self):
        member = self.create_member()

        with patch(
            "apps.members.services.member_service." "AuditService.record_event",
            side_effect=RuntimeError("Audit failure"),
        ):
            with self.assertRaises(RuntimeError):
                update_member(
                    member=member,
                    actor=self.pastor,
                    full_name="Updated Member",
                )

        member.refresh_from_db()

        self.assertEqual(member.full_name, "Test Member")
        self.assertIsNone(member.updated_by)

        self.assertEqual(
            AuditLog.objects.filter(
                entity_type="Member",
                entity_id=member.id,
                action=AuditLog.Action.UPDATE,
            ).count(),
            0,
        )
