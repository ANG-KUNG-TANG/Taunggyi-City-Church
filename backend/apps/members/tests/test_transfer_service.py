from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.members.models import Member
from apps.members.services.member_service import create_member
from apps.members.services.member_transfer_service import transfer_member
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class MemberTransferServiceTests(TestCase):
    def setUp(self):
        self.pastor = User.objects.create_user(
            email="pastor@example.com",
            password="test-password",
        )

        self.leader = User.objects.create_user(
            email="leader@example.com",
            password="test-password",
        )

        self.ordinary_user = User.objects.create_user(
            email="ordinary@example.com",
            password="test-password",
        )

        self.pastor_role = Role.objects.get(code="PASTOR")
        self.leader_role = Role.objects.get(code="ZONE_LEADER")

        self.assign_role(self.pastor, self.pastor_role)
        self.assign_role(self.leader, self.leader_role)

        self.zone = Zone.objects.create(name="Zone A")
        self.other_zone = Zone.objects.create(name="Zone B")

        ZoneLeaderAssignment.objects.create(
            zone=self.zone,
            user=self.leader,
            assigned_by=self.pastor,
            effective_from=timezone.now(),
        )

    def assign_role(self, user, role):
        return UserRole.objects.create(
            user=user,
            role=role,
        )

    def create_member(self):
        return create_member(
            zone=self.zone,
            full_name="Transfer Test Member",
            actor=self.pastor,
        )

    def test_pastor_can_transfer_member_to_another_active_zone(self):
        member = self.create_member()

        transferred = transfer_member(
            member=member,
            destination_zone=self.other_zone,
            actor=self.pastor,
        )

        transferred.refresh_from_db()

        self.assertEqual(transferred.zone, self.other_zone)
        self.assertEqual(transferred.updated_by, self.pastor)

        audit = AuditLog.objects.get(
            entity_type="Member",
            entity_id=member.id,
            action=AuditLog.Action.UPDATE,
        )

        self.assertEqual(audit.actor, self.pastor)
        self.assertEqual(
            audit.before_data["zone_id"],
            str(self.zone.id),
        )
        self.assertEqual(
            audit.after_data["zone_id"],
            str(self.other_zone.id),
        )

    def test_zone_leader_cannot_transfer_member(self):
        member = self.create_member()

        with self.assertRaises(ValidationError):
            transfer_member(
                member=member,
                destination_zone=self.other_zone,
                actor=self.leader,
            )

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertIsNone(member.updated_by)

        self.assertFalse(
            AuditLog.objects.filter(
                entity_type="Member",
                entity_id=member.id,
                action=AuditLog.Action.UPDATE,
            ).exists()
        )

    def test_user_without_pastor_role_cannot_transfer_member(self):
        member = self.create_member()

        with self.assertRaises(ValidationError):
            transfer_member(
                member=member,
                destination_zone=self.other_zone,
                actor=self.ordinary_user,
            )

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertIsNone(member.updated_by)

    def test_inactive_pastor_cannot_transfer_member(self):
        member = self.create_member()

        self.pastor.is_active = False
        self.pastor.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            transfer_member(
                member=member,
                destination_zone=self.other_zone,
                actor=self.pastor,
            )

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertIsNone(member.updated_by)

    def test_transfer_to_inactive_zone_is_rejected(self):
        member = self.create_member()

        self.other_zone.is_active = False
        self.other_zone.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            transfer_member(
                member=member,
                destination_zone=self.other_zone,
                actor=self.pastor,
            )

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertIsNone(member.updated_by)

    def test_transfer_to_current_zone_is_rejected(self):
        member = self.create_member()

        with self.assertRaises(ValidationError):
            transfer_member(
                member=member,
                destination_zone=self.zone,
                actor=self.pastor,
            )

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertIsNone(member.updated_by)

    def test_audit_failure_rolls_back_transfer(self):
        member = self.create_member()

        with patch(
            "apps.members.services.member_transfer_service."
            "AuditService.record_event",
            side_effect=RuntimeError("Audit failure"),
        ):
            with self.assertRaises(RuntimeError):
                transfer_member(
                    member=member,
                    destination_zone=self.other_zone,
                    actor=self.pastor,
                )

        member.refresh_from_db()

        self.assertEqual(member.zone, self.zone)
        self.assertIsNone(member.updated_by)

        self.assertFalse(
            AuditLog.objects.filter(
                entity_type="Member",
                entity_id=member.id,
                action=AuditLog.Action.UPDATE,
            ).exists()
        )
