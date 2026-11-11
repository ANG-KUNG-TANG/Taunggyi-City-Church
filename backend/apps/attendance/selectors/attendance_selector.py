"""Read-only selectors for Attendance records and reports."""

from django.db.models import (
    Count,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce

from apps.attendance.models.attendance_session import AttendanceSession
from apps.attendance.models.member_attendance import MemberAttendance
from apps.attendance.models.visitor_count import VisitorCount
from apps.attendance.selectors.session_selector import (
    AttendanceSessionSelector,
)


class AttendanceSelector:
    """Scoped queries for Attendance records and reports."""

    @staticmethod
    def get_member_records_for_session(*, user, session_id):
        """Return member records only for an accessible session."""

        session = AttendanceSessionSelector.get_session_for_user(
            user=user,
            session_id=session_id,
        )

        if session is None:
            return MemberAttendance.objects.none()

        return MemberAttendance.objects.filter(
            session=session,
        ).select_related(
            "member",
            "recorded_by",
            "updated_by",
        )

    @staticmethod
    def get_visitor_count_for_session(*, user, session_id):
        """Return visitor counts only for accessible sessions."""

        session = AttendanceSessionSelector.get_session_for_user(
            user=user,
            session_id=session_id,
        )

        if session is None:
            return VisitorCount.objects.none()

        return VisitorCount.objects.filter(
            session=session,
        ).select_related(
            "recorded_by",
            "updated_by",
        )

    @staticmethod
    def get_report_queryset(*, user, start_date=None, end_date=None):
        """Return sessions restricted to the user's authorised scope."""

        sessions = AttendanceSessionSelector.get_sessions_for_user(
            user,
        ).select_related(
            "zone",
            "activity",
        )

        if start_date is not None:
            sessions = sessions.filter(date__gte=start_date)

        if end_date is not None:
            sessions = sessions.filter(date__lte=end_date)

        return sessions

    @staticmethod
    def get_session_report(*, user, start_date=None, end_date=None):
        """Return accurate aggregate attendance data for accessible sessions."""

        visitor_count_subquery = VisitorCount.objects.filter(
            session_id=OuterRef("pk"),
        ).values("count",)[:1]

        sessions = AttendanceSelector.get_report_queryset(
            user=user,
            start_date=start_date,
            end_date=end_date,
        )

        return sessions.annotate(
            present_count=Count(
                "member_attendance",
                filter=Q(
                    member_attendance__status=MemberAttendance.Status.PRESENT,
                ),
                distinct=True,
            ),
            absent_count=Count(
                "member_attendance",
                filter=Q(
                    member_attendance__status=MemberAttendance.Status.ABSENT,
                ),
                distinct=True,
            ),
            visitor_count=Coalesce(
                Subquery(
                    visitor_count_subquery,
                    output_field=IntegerField(),
                ),
                Value(0),
                output_field=IntegerField(),
            ),
        ).order_by(
            "-date",
            "-start_time",
        )
