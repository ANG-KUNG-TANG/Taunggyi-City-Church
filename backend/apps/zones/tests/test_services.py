from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.zones.models.zones import Zone, ZoneLeaderAssignment
from apps.zones.services.zone_service import (
    assign_zone_leader,
    create_zone,
    deactivate_zone,
    end_zone_leader_assignment,
    update_zone,
)


class ZoneServiceTests(TestCase):
    def setUp(self):
        self.pastor = User.objects.create_user(
            email="pastor@example.com",
            password="test-password",
        )

        self.leader = User.objects.create_user(
            email="leader@example.com",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
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

        self.zone = Zone.objects.create(
            name="North Zone",
            description="North church community",
        )

    def test_pastor_can_create_zone(self):
        zone = create_zone(
            name="South Zone",
            actor=self.pastor,
        )

        self.assertEqual(zone.name, "South Zone")
        self.assertTrue(zone.is_active)

    def test_zone_name_is_trimmed(self):
        zone = create_zone(
            name="  South Zone  ",
            actor=self.pastor,
        )

        self.assertEqual(zone.name, "South Zone")

    def test_non_pastor_cannot_create_zone(self):
        with self.assertRaises(ValidationError):
            create_zone(
                name="South Zone",
                actor=self.leader,
            )

    def test_inactive_pastor_cannot_create_zone(self):
        self.pastor.is_active = False
        self.pastor.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            create_zone(
                name="South Zone",
                actor=self.pastor,
            )

    def test_blank_zone_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_zone(
                name="   ",
                actor=self.pastor,
            )

    def test_duplicate_zone_name_is_rejected_case_insensitively(self):
        with self.assertRaises(ValidationError):
            create_zone(
                name="north zone",
                actor=self.pastor,
            )

    def test_zone_name_over_100_characters_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_zone(
                name="A" * 101,
                actor=self.pastor,
            )

    def test_pastor_can_update_zone(self):
        updated = update_zone(
            zone=self.zone,
            actor=self.pastor,
            name="Central Zone",
            description="Updated description",
        )

        self.assertEqual(updated.name, "Central Zone")
        self.assertEqual(updated.description, "Updated description")

    def test_duplicate_zone_name_is_rejected_on_update(self):
        Zone.objects.create(name="South Zone")

        with self.assertRaises(ValidationError):
            update_zone(
                zone=self.zone,
                actor=self.pastor,
                name="South Zone",
            )

    def test_pastor_can_deactivate_zone(self):
        deactivated = deactivate_zone(
            zone=self.zone,
            actor=self.pastor,
        )

        self.assertFalse(deactivated.is_active)
        self.assertTrue(Zone.objects.filter(pk=self.zone.pk).exists())

    def test_pastor_can_assign_zone_leader(self):
        assignment = assign_zone_leader(
            zone=self.zone,
            user=self.leader,
            actor=self.pastor,
        )

        self.assertEqual(assignment.zone, self.zone)
        self.assertEqual(assignment.user, self.leader)
        self.assertEqual(assignment.assigned_by, self.pastor)
        self.assertIsNone(assignment.effective_to)

    def test_non_pastor_cannot_assign_zone_leader(self):
        with self.assertRaises(ValidationError):
            assign_zone_leader(
                zone=self.zone,
                user=self.leader,
                actor=self.leader,
            )

    def test_inactive_zone_cannot_receive_assignment(self):
        self.zone.is_active = False
        self.zone.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            assign_zone_leader(
                zone=self.zone,
                user=self.leader,
                actor=self.pastor,
            )

    def test_user_without_zone_leader_role_cannot_be_assigned(self):
        with self.assertRaises(ValidationError):
            assign_zone_leader(
                zone=self.zone,
                user=self.other_user,
                actor=self.pastor,
            )

    def test_duplicate_active_assignment_is_rejected(self):
        assign_zone_leader(
            zone=self.zone,
            user=self.leader,
            actor=self.pastor,
        )

        with self.assertRaises(ValidationError):
            assign_zone_leader(
                zone=self.zone,
                user=self.leader,
                actor=self.pastor,
            )

    def test_assignment_can_be_ended(self):
        assignment = assign_zone_leader(
            zone=self.zone,
            user=self.leader,
            actor=self.pastor,
        )

        end_time = assignment.effective_from + timedelta(days=1)

        ended = end_zone_leader_assignment(
            assignment=assignment,
            actor=self.pastor,
            effective_to=end_time,
        )

        self.assertEqual(ended.effective_to, end_time)

    def test_ended_assignment_is_preserved(self):
        assignment = assign_zone_leader(
            zone=self.zone,
            user=self.leader,
            actor=self.pastor,
        )

        end_zone_leader_assignment(
            assignment=assignment,
            actor=self.pastor,
        )

        self.assertTrue(
            ZoneLeaderAssignment.objects.filter(
                pk=assignment.pk,
            ).exists()
        )

    def test_assignment_cannot_end_before_start(self):
        assignment = assign_zone_leader(
            zone=self.zone,
            user=self.leader,
            actor=self.pastor,
        )

        invalid_end = assignment.effective_from - timedelta(days=1)

        with self.assertRaises(ValidationError):
            end_zone_leader_assignment(
                assignment=assignment,
                actor=self.pastor,
                effective_to=invalid_end,
            )

    def test_assignment_cannot_be_ended_twice(self):
        assignment = assign_zone_leader(
            zone=self.zone,
            user=self.leader,
            actor=self.pastor,
        )

        end_zone_leader_assignment(
            assignment=assignment,
            actor=self.pastor,
        )

        assignment.refresh_from_db()

        with self.assertRaises(ValidationError):
            end_zone_leader_assignment(
                assignment=assignment,
                actor=self.pastor,
            )
