"""
Read-only Attendance session selectors.

All session queries are scoped before records are returned
to API views or serializers.
"""

from django.db.models import Q
from django.utils import timezone

from apps.attendance.models.attendance_session import AttendanceSession
from apps.zones.models.zones import Zone


class AttendanceSessionSelector:
    """Read-only queries for Attendance sessions."""

    @staticmethod
    def get_sessions_for_user(user):
        """
        Return sessions accessible to the supplied user.

        Pastor:
            Can access all Attendance sessions.

        Zone Leader:
            Can access sessions belonging to currently assigned
            active zones.

        Other users:
            Receive an empty queryset.

        Church-wide sessions:
            Accessible to Pastors only.
        """

        if not user or not user.is_authenticated:
            return AttendanceSession.objects.none()

        if not user.is_active:
            return AttendanceSession.objects.none()

        active_roles = set(
            user.role_assignments.filter(
                revoked_at__isnull=True,
            ).values_list(
                "role__code",
                flat=True,
            )
        )

        if "PASTOR" in active_roles:
            return AttendanceSession.objects.all()

        if "ZONE_LEADER" not in active_roles:
            return AttendanceSession.objects.none()

        now = timezone.now()

        accessible_zones = (
            Zone.objects.filter(
                is_active=True,
                leader_assignments__user=user,
                leader_assignments__effective_from__lte=now,
            )
            .filter(
                Q(leader_assignments__effective_to__isnull=True)
                | Q(leader_assignments__effective_to__gt=now)
            )
            .distinct()
        )

        return AttendanceSession.objects.filter(
            scope=AttendanceSession.Scope.ZONE,
            zone__in=accessible_zones,
        ).distinct()

    @staticmethod
    def get_session_for_user(*, user, session_id):
        """
        Retrieve one session only when it is accessible to the user.

        Unauthorized sessions are not returned.
        """

        return (
            AttendanceSessionSelector.get_sessions_for_user(
                user,
            )
            .filter(
                id=session_id,
            )
            .first()
        )

    @staticmethod
    def get_sessions_for_zone(*, user, zone_id):
        """
        Return accessible sessions restricted to one zone.

        The user-accessible queryset is applied first, so a
        requested zone cannot bypass role or assignment scope.
        """

        return AttendanceSessionSelector.get_sessions_for_user(
            user,
        ).filter(
            scope=AttendanceSession.Scope.ZONE,
            zone_id=zone_id,
        )
