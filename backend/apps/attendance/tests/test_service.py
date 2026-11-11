from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.role import Role
from apps.accounts.models.user_role import UserRole
from apps.accounts.models.users import User
from apps.audit.models.audit_log import AuditLog
from apps.attendance.models.attendance_session import AttendanceSession
from apps.attendance.models.member_attendance import MemberAttendance
from apps.attendance.models.visitor_count import VisitorCount
from apps.attendance.services.attendance_service import AttendanceService
from apps.members.models import Member
from apps.zones.models.zones import Zone, ZoneLeaderAssignment


class AttendanceServiceTests(TestCase):
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
            email="ordinary@example.com",
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

        self.member = Member.objects.create(
            zone=self.zone,
            full_name="Test Member",
            created_by=self.pastor,
        )

        self.other_member = Member.objects.create(
            zone=self.other_zone,
            full_name="Other Zone Member",
            created_by=self.pastor,
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

    def create_session(
        self,
        *,
        actor=None,
        scope=AttendanceSession.Scope.ZONE,
        zone=None,
    ):
        return AttendanceService.create_session(
            actor=actor or self.pastor,
            date=date.today(),
            start_time=time(10, 0),
            scope=scope,
            zone=zone or self.zone,
        )

    def open_session(self, *, session, actor=None):
        return AttendanceService.open_session(
            actor=actor or self.pastor,
            session_id=session.id,
        )

    def close_session(self, *, session, actor=None):
        return AttendanceService.close_session(
            actor=actor or self.pastor,
            session_id=session.id,
        )

    # ---------------------------------------------------------
    # Session creation and authorization
    # ---------------------------------------------------------

    def test_pastor_can_create_church_wide_session(self):
        session = AttendanceService.create_session(
            actor=self.pastor,
            date=date.today(),
            start_time=time(10, 0),
            scope=AttendanceSession.Scope.CHURCH_WIDE,
        )

        self.assertEqual(
            session.scope,
            AttendanceSession.Scope.CHURCH_WIDE,
        )
        self.assertIsNone(session.zone)
        self.assertEqual(
            session.status,
            AttendanceSession.Status.DRAFT,
        )
        self.assertEqual(session.created_by, self.pastor)

        audit = AuditLog.objects.get(
            entity_type="AttendanceSession",
            entity_id=session.id,
            action=AuditLog.Action.CREATE,
        )

        self.assertEqual(audit.actor, self.pastor)
        self.assertEqual(
            audit.after_data["scope"],
            AttendanceSession.Scope.CHURCH_WIDE,
        )

    def test_zone_leader_can_create_session_in_assigned_zone(self):
        session = self.create_session(
            actor=self.leader,
            zone=self.zone,
        )

        self.assertEqual(session.zone, self.zone)
        self.assertEqual(session.created_by, self.leader)

    def test_zone_leader_cannot_create_session_in_unassigned_zone(self):
        with self.assertRaises(ValidationError):
            self.create_session(
                actor=self.leader,
                zone=self.other_zone,
            )

        self.assertEqual(AttendanceSession.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_ordinary_user_cannot_create_session(self):
        with self.assertRaises(ValidationError):
            self.create_session(actor=self.ordinary_user)

        self.assertEqual(AttendanceSession.objects.count(), 0)

    def test_church_wide_session_requires_pastor(self):
        with self.assertRaises(ValidationError):
            AttendanceService.create_session(
                actor=self.leader,
                date=date.today(),
                start_time=time(10, 0),
                scope=AttendanceSession.Scope.CHURCH_WIDE,
            )

        self.assertEqual(AttendanceSession.objects.count(), 0)

    # ---------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------

    def test_session_can_be_opened_and_closed(self):
        session = self.create_session(actor=self.leader)

        opened = self.open_session(
            session=session,
            actor=self.leader,
        )

        self.assertEqual(
            opened.status,
            AttendanceSession.Status.OPEN,
        )
        self.assertEqual(opened.updated_by, self.leader)

        closed = self.close_session(
            session=opened,
            actor=self.leader,
        )

        self.assertEqual(
            closed.status,
            AttendanceSession.Status.CLOSED,
        )
        self.assertEqual(closed.updated_by, self.leader)

    def test_session_cannot_be_opened_twice(self):
        session = self.create_session(actor=self.leader)

        self.open_session(
            session=session,
            actor=self.leader,
        )

        with self.assertRaises(ValidationError):
            self.open_session(
                session=session,
                actor=self.leader,
            )

    # ---------------------------------------------------------
    # Member attendance
    # ---------------------------------------------------------

    def test_zone_leader_can_record_member_attendance(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        record = AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        self.assertEqual(record.session, session)
        self.assertEqual(record.member, self.member)
        self.assertEqual(
            record.status,
            MemberAttendance.Status.PRESENT,
        )
        self.assertEqual(record.recorded_by, self.leader)

        self.assertEqual(
            MemberAttendance.objects.filter(
                session=session,
                member=self.member,
            ).count(),
            1,
        )

        audit = AuditLog.objects.get(
            entity_type="MemberAttendance",
            entity_id=record.id,
            action=AuditLog.Action.CREATE,
        )

        self.assertEqual(audit.actor, self.leader)
        self.assertEqual(
            audit.after_data["status"],
            MemberAttendance.Status.PRESENT,
        )

    def test_zone_leader_cannot_record_member_from_another_zone(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        with self.assertRaises(ValidationError):
            AttendanceService.record_member_attendance(
                actor=self.leader,
                session_id=session.id,
                member_id=self.other_member.id,
                status=MemberAttendance.Status.PRESENT,
            )

        self.assertEqual(MemberAttendance.objects.count(), 0)

    def test_recording_existing_member_updates_status(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        first_record = AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        updated_record = AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.ABSENT,
        )

        first_record.refresh_from_db()

        self.assertEqual(first_record.id, updated_record.id)
        self.assertEqual(
            updated_record.status,
            MemberAttendance.Status.ABSENT,
        )
        self.assertEqual(updated_record.updated_by, self.leader)

        self.assertEqual(
            MemberAttendance.objects.filter(
                session=session,
                member=self.member,
            ).count(),
            1,
        )

        self.assertEqual(
            AuditLog.objects.filter(
                entity_type="MemberAttendance",
                entity_id=updated_record.id,
            ).count(),
            2,
        )

    def test_recording_same_status_does_not_create_extra_audit(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        first_record = AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        second_record = AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        self.assertEqual(first_record.id, second_record.id)

        self.assertEqual(
            AuditLog.objects.filter(
                entity_type="MemberAttendance",
                entity_id=first_record.id,
            ).count(),
            1,
        )

    # ---------------------------------------------------------
    # Visitor count
    # ---------------------------------------------------------

    def test_zone_leader_can_record_visitor_count(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        record = AttendanceService.record_visitor_count(
            actor=self.leader,
            session_id=session.id,
            count=12,
        )

        self.assertEqual(record.session, session)
        self.assertEqual(record.count, 12)
        self.assertEqual(record.recorded_by, self.leader)

        audit = AuditLog.objects.get(
            entity_type="VisitorCount",
            entity_id=record.id,
            action=AuditLog.Action.CREATE,
        )

        self.assertEqual(audit.actor, self.leader)
        self.assertEqual(audit.after_data["count"], 12)

    def test_recording_visitor_count_updates_existing_record(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        first_record = AttendanceService.record_visitor_count(
            actor=self.leader,
            session_id=session.id,
            count=12,
        )

        updated_record = AttendanceService.record_visitor_count(
            actor=self.leader,
            session_id=session.id,
            count=15,
        )

        first_record.refresh_from_db()

        self.assertEqual(first_record.id, updated_record.id)
        self.assertEqual(updated_record.count, 15)
        self.assertEqual(updated_record.updated_by, self.leader)

        self.assertEqual(
            VisitorCount.objects.filter(session=session).count(),
            1,
        )

        self.assertEqual(
            AuditLog.objects.filter(
                entity_type="VisitorCount",
                entity_id=updated_record.id,
            ).count(),
            2,
        )

    def test_negative_visitor_count_is_rejected(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        with self.assertRaises(ValidationError):
            AttendanceService.record_visitor_count(
                actor=self.leader,
                session_id=session.id,
                count=-1,
            )

        self.assertEqual(VisitorCount.objects.count(), 0)

    def test_boolean_visitor_count_is_rejected(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        with self.assertRaises(ValidationError):
            AttendanceService.record_visitor_count(
                actor=self.leader,
                session_id=session.id,
                count=True,
            )

        self.assertEqual(VisitorCount.objects.count(), 0)

    # ---------------------------------------------------------
    # Corrections
    # ---------------------------------------------------------

    def test_pastor_can_correct_closed_member_attendance(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        record = AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        self.close_session(
            session=session,
            actor=self.leader,
        )

        corrected = AttendanceService.correct_member_attendance(
            actor=self.pastor,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.ABSENT,
            reason="Attendance was recorded incorrectly.",
        )

        self.assertEqual(corrected.id, record.id)
        self.assertEqual(
            corrected.status,
            MemberAttendance.Status.ABSENT,
        )
        self.assertEqual(corrected.updated_by, self.pastor)

        audit = AuditLog.objects.get(
            entity_type="MemberAttendance",
            entity_id=record.id,
            action=AuditLog.Action.CORRECT,
        )

        self.assertEqual(audit.actor, self.pastor)
        self.assertEqual(
            audit.before_data["status"],
            MemberAttendance.Status.PRESENT,
        )
        self.assertEqual(
            audit.after_data["status"],
            MemberAttendance.Status.ABSENT,
        )
        self.assertEqual(
            audit.after_data["correction_reason"],
            "Attendance was recorded incorrectly.",
        )

    def test_zone_leader_cannot_correct_closed_attendance(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        self.close_session(
            session=session,
            actor=self.leader,
        )

        with self.assertRaises(ValidationError):
            AttendanceService.correct_member_attendance(
                actor=self.leader,
                session_id=session.id,
                member_id=self.member.id,
                status=MemberAttendance.Status.ABSENT,
                reason="Correction attempt.",
            )

    def test_correction_requires_reason(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        AttendanceService.record_member_attendance(
            actor=self.leader,
            session_id=session.id,
            member_id=self.member.id,
            status=MemberAttendance.Status.PRESENT,
        )

        self.close_session(
            session=session,
            actor=self.leader,
        )

        with self.assertRaises(ValidationError):
            AttendanceService.correct_member_attendance(
                actor=self.pastor,
                session_id=session.id,
                member_id=self.member.id,
                status=MemberAttendance.Status.ABSENT,
                reason="   ",
            )

    def test_pastor_can_correct_closed_visitor_count(self):
        session = self.create_session(actor=self.leader)
        self.open_session(
            session=session,
            actor=self.leader,
        )

        record = AttendanceService.record_visitor_count(
            actor=self.leader,
            session_id=session.id,
            count=12,
        )

        self.close_session(
            session=session,
            actor=self.leader,
        )

        corrected = AttendanceService.correct_visitor_count(
            actor=self.pastor,
            session_id=session.id,
            count=14,
            reason="Two visitors were omitted.",
        )

        self.assertEqual(corrected.id, record.id)
        self.assertEqual(corrected.count, 14)
        self.assertEqual(corrected.updated_by, self.pastor)

        audit = AuditLog.objects.get(
            entity_type="VisitorCount",
            entity_id=record.id,
            action=AuditLog.Action.CORRECT,
        )

        self.assertEqual(audit.actor, self.pastor)
        self.assertEqual(audit.before_data["count"], 12)
        self.assertEqual(audit.after_data["count"], 14)
        self.assertEqual(
            audit.after_data["correction_reason"],
            "Two visitors were omitted.",
        )
