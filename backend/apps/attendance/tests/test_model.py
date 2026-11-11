from datetime import time

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.users import User
from apps.attendance.models import (
    AttendanceSession,
    MemberAttendance,
    VisitorCount,
)
from apps.members.models import Member
from apps.zones.models.zones import Zone


class AttendanceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="model-pastor@example.com",
            password="TestPassword123!",
        )

        self.zone = Zone.objects.create(name="Model Test Zone")

        self.member = Member.objects.create(
            zone=self.zone,
            full_name="Model Test Member",
            created_by=self.user,
        )

    def create_session(self):
        return AttendanceSession.objects.create(
            date=timezone.localdate(),
            start_time=time(10, 0),
            scope=AttendanceSession.Scope.ZONE,
            zone=self.zone,
            created_by=self.user,
        )

    def test_attendance_session_has_uuid_primary_key(self):
        session = self.create_session()

        self.assertIsNotNone(session.id)
        self.assertEqual(session.pk, session.id)

    def test_attendance_session_defaults_to_draft(self):
        session = self.create_session()

        self.assertEqual(
            session.status,
            AttendanceSession.Status.DRAFT,
        )

    def test_attendance_session_records_timestamps(self):
        session = self.create_session()

        self.assertIsNotNone(session.created_at)
        self.assertIsNotNone(session.updated_at)

    def test_member_attendance_can_be_created(self):
        session = self.create_session()

        record = MemberAttendance.objects.create(
            session=session,
            member=self.member,
            status=MemberAttendance.Status.PRESENT,
            recorded_by=self.user,
        )

        self.assertIsNotNone(record.id)
        self.assertEqual(record.session, session)
        self.assertEqual(record.member, self.member)
        self.assertEqual(record.status, MemberAttendance.Status.PRESENT)
        self.assertIsNotNone(record.recorded_at)
        self.assertIsNotNone(record.updated_at)

    def test_visitor_count_defaults_to_zero(self):
        session = self.create_session()

        record = VisitorCount.objects.create(
            session=session,
            recorded_by=self.user,
        )

        self.assertEqual(record.count, 0)
        self.assertEqual(record.session, session)
        self.assertIsNotNone(record.recorded_at)

    def test_session_reverse_relationships(self):
        session = self.create_session()

        MemberAttendance.objects.create(
            session=session,
            member=self.member,
            status=MemberAttendance.Status.PRESENT,
            recorded_by=self.user,
        )

        VisitorCount.objects.create(
            session=session,
            count=3,
            recorded_by=self.user,
        )

        self.assertEqual(session.member_attendance.count(), 1)
        self.assertEqual(session.visitor_count.count, 3)
