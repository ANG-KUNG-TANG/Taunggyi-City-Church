"""Unit tests for Attendance serializers."""

from uuid import uuid4

from django.test import SimpleTestCase

from apps.attendance.serializers.attendance_serializer import (
    AttendanceCorrectionSerializer,
    MemberAttendanceBulkSerializer,
    MemberAttendanceInputSerializer,
)
from apps.attendance.serializers.session_serializers import (
    AttendanceSessionCreateSerializer,
    AttendanceSessionUpdateSerializer,
)
from apps.attendance.serializers.visitor_count_serializer import (
    VisitorCountCorrectionSerializer,
    VisitorCountInputSerializer,
)


class AttendanceSessionSerializerTests(SimpleTestCase):
    def test_valid_zone_session_requires_and_accepts_zone(self):
        serializer = AttendanceSessionCreateSerializer(
            data={
                "date": "2026-11-11",
                "start_time": "09:00:00",
                "scope": "ZONE",
                "zone_id": str(uuid4()),
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_zone_session_without_zone_is_rejected(self):
        serializer = AttendanceSessionCreateSerializer(
            data={
                "date": "2026-11-11",
                "start_time": "09:00:00",
                "scope": "ZONE",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("zone_id", serializer.errors)

    def test_church_wide_session_without_zone_is_valid(self):
        serializer = AttendanceSessionCreateSerializer(
            data={
                "date": "2026-11-11",
                "start_time": "09:00:00",
                "scope": "CHURCH_WIDE",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_church_wide_session_with_zone_is_rejected(self):
        serializer = AttendanceSessionCreateSerializer(
            data={
                "date": "2026-11-11",
                "start_time": "09:00:00",
                "scope": "CHURCH_WIDE",
                "zone_id": str(uuid4()),
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("zone_id", serializer.errors)

    def test_invalid_session_scope_is_rejected(self):
        serializer = AttendanceSessionCreateSerializer(
            data={
                "date": "2026-11-11",
                "start_time": "09:00:00",
                "scope": "INVALID",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("scope", serializer.errors)

    def test_empty_session_update_is_rejected(self):
        serializer = AttendanceSessionUpdateSerializer(data={})

        self.assertFalse(serializer.is_valid())

    def test_valid_session_update_is_accepted(self):
        serializer = AttendanceSessionUpdateSerializer(data={"date": "2026-11-12"})

        self.assertTrue(serializer.is_valid(), serializer.errors)


class MemberAttendanceSerializerTests(SimpleTestCase):
    def test_valid_member_attendance_input_is_accepted(self):
        serializer = MemberAttendanceInputSerializer(
            data={
                "member_id": str(uuid4()),
                "status": "PRESENT",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_member_attendance_status_is_rejected(self):
        serializer = MemberAttendanceInputSerializer(
            data={
                "member_id": str(uuid4()),
                "status": "LATE",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_bulk_attendance_accepts_unique_members(self):
        serializer = MemberAttendanceBulkSerializer(
            data={
                "records": [
                    {"member_id": str(uuid4()), "status": "PRESENT"},
                    {"member_id": str(uuid4()), "status": "ABSENT"},
                ]
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_bulk_attendance_rejects_duplicate_members(self):
        member_id = str(uuid4())

        serializer = MemberAttendanceBulkSerializer(
            data={
                "records": [
                    {"member_id": member_id, "status": "PRESENT"},
                    {"member_id": member_id, "status": "ABSENT"},
                ]
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("records", serializer.errors)

    def test_bulk_attendance_rejects_empty_records(self):
        serializer = MemberAttendanceBulkSerializer(data={"records": []})

        self.assertFalse(serializer.is_valid())
        self.assertIn("records", serializer.errors)

    def test_correction_requires_non_empty_reason(self):
        serializer = AttendanceCorrectionSerializer(
            data={"status": "PRESENT", "reason": "   "}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("reason", serializer.errors)

    def test_correction_trims_reason_whitespace(self):
        serializer = AttendanceCorrectionSerializer(
            data={
                "status": "ABSENT",
                "reason": "  Incorrect entry  ",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["reason"],
            "Incorrect entry",
        )


class VisitorCountSerializerTests(SimpleTestCase):
    def test_zero_visitor_count_is_valid(self):
        serializer = VisitorCountInputSerializer(data={"count": 0})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_positive_visitor_count_is_valid(self):
        serializer = VisitorCountInputSerializer(data={"count": 12})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_negative_visitor_count_is_rejected(self):
        serializer = VisitorCountInputSerializer(data={"count": -1})

        self.assertFalse(serializer.is_valid())
        self.assertIn("count", serializer.errors)

    def test_visitor_count_correction_requires_reason(self):
        serializer = VisitorCountCorrectionSerializer(data={"count": 5, "reason": ""})

        self.assertFalse(serializer.is_valid())
        self.assertIn("reason", serializer.errors)

    def test_valid_visitor_count_correction_is_accepted(self):
        serializer = VisitorCountCorrectionSerializer(
            data={
                "count": 8,
                "reason": "  Recount confirmed  ",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["count"], 8)
        self.assertEqual(
            serializer.validated_data["reason"],
            "Recount confirmed",
        )
