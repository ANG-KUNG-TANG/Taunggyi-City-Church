"""
Member API permissions.

Pastors can access members across all zones.
Zone leaders can access members only in their currently assigned zones.
Administrators do not receive implicit member access.
"""

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import BasePermission

from apps.zones.models.zones import ZoneLeaderAssignment


class CanAccessMembers(BasePermission):
    """
    Allow active pastors and zone leaders to access member operations.

    Object-level checks restrict zone leaders to members belonging
    to zones currently assigned to them.
    """

    message = "You do not have permission to access this member."

    def has_active_role(self, user, role_code):
        """
        Return True when the user has an active, unrevoked role.
        """
        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        return user.role_assignments.filter(
            role__code=role_code,
            revoked_at__isnull=True,
        ).exists()

    def has_permission(self, request, view):
        """
        Grant request-level access to pastors and zone leaders.
        """
        user = request.user

        return self.has_active_role(user, "PASTOR") or self.has_active_role(
            user, "ZONE_LEADER"
        )

    def has_object_permission(self, request, view, obj):
        """
        Restrict member access to active zones.

        Pastors can access members in all active zones.
        Zone leaders can access members only in their
        currently assigned active zones.
        """
        user = request.user

        # Members in inactive zones are not accessible.
        if not obj.zone.is_active:
            return False

        if self.has_active_role(user, "PASTOR"):
            return True

        if not self.has_active_role(user, "ZONE_LEADER"):
            return False

        now = timezone.now()

        return (
            ZoneLeaderAssignment.objects.filter(
                zone=obj.zone,
                user=user,
                effective_from__lte=now,
            )
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gt=now))
            .exists()
        )
