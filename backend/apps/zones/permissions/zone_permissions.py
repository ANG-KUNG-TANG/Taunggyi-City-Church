"""
Zone API permissions.

Pastors can read all zones.
Zone leaders can read zones assigned to them.
Only pastors can manage zones and zone leader assignments.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions.role_permission import IsPastor


def has_active_role(user, role_code):
    """
    Return True if the authenticated, active user has an
    unrevoked assignment for the requested role.
    """
    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    return user.role_assignments.filter(
        role__code=role_code,
        revoked_at__isnull=True,
    ).exists()


class CanReadZones(BasePermission):
    """
    Allow pastors and active zone leaders to read zones.

    Zone-level filtering is handled by the API view.
    """

    message = "You do not have permission to view zones."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        return has_active_role(user, "PASTOR") or has_active_role(user, "ZONE_LEADER")


class IsPastorForZoneManagement(IsPastor):
    """
    Restrict zone management to pastors.
    """

    pass
