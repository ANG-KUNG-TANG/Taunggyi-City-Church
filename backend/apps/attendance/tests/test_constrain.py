from datetime import time
from django.db import IntegrityError, transaction
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


class AttendanceConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="constraint-pastor@example.com",
            password="TestPassword123!",
        )

        self.zone = Zone.objects.create(name="Constraint Test Zone")

        self.member = Member.objects.create(
            zone=self.zone,
            full_name="Constraint Test Member",
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

    def test_zone_session_requires_zone(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AttendanceSession.objects.create(
                    date=timezone.localdate(),
                    start_time=time(10, 0),
                    scope=AttendanceSession.Scope.ZONE,
                    zone=None,
                    created_by=self.user,
                )

    def test_church_wide_session_must_not_have_zone(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AttendanceSession.objects.create(
                    date=timezone.localdate(),
                    start_time=time(10, 0),
                    scope=AttendanceSession.Scope.CHURCH_WIDE,
                    zone=self.zone,
                    created_by=self.user,
                )

    def test_duplicate_member_attendance_is_rejected(self):
        session = self.create_session()

        MemberAttendance.objects.create(
            session=session,
            member=self.member,
            status=MemberAttendance.Status.PRESENT,
            recorded_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MemberAttendance.objects.create(
                    session=session,
                    member=self.member,
                    status=MemberAttendance.Status.ABSENT,
                    recorded_by=self.user,
                )

    def test_duplicate_visitor_count_for_session_is_rejected(self):
        session = self.create_session()

        VisitorCount.objects.create(
            session=session,
            count=2,
            recorded_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VisitorCount.objects.create(
                    session=session,
                    count=5,
                    recorded_by=self.user,
                )
