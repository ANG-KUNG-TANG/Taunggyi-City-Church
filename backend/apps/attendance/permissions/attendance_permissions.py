"""
Attendance permissions for Taunggyi City Church.

Attendance access is restricted to active Pastors and Zone Leaders.
Administrators do not automatically receive Attendance access.
"""

from rest_framework.permissions import BasePermission

from apps.zones.permissions.zone_permissions import has_active_role


class IsAttendanceActor(BasePermission):
    """
    Allow active Pastors and Zone Leaders to use Attendance endpoints.
    """

    message = "Only Pastors and Zone Leaders may access Attendance."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        return has_active_role(user, "PASTOR") or has_active_role(user, "ZONE_LEADER")


class IsAttendancePastor(BasePermission):
    """
    Restrict an operation to an active Pastor.
    """

    message = "Only an active Pastor may perform this operation."

    def has_permission(self, request, view):
        return has_active_role(request.user, "PASTOR")


class IsAttendanceZoneLeader(BasePermission):
    """
    Restrict an operation to an active Zone Leader.
    """

    message = "Only an active Zone Leader may perform this operation."

    def has_permission(self, request, view):
        return has_active_role(request.user, "ZONE_LEADER")
