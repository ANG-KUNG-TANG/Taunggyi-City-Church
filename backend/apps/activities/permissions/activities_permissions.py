"""
Activity permissions for the Taunggyi City Church system.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions.role_permission import (
    IsPastorOrAdministrator,
)


class CanPublishActivity(IsPastorOrAdministrator):
    """
    Only active Pastors and Administrators may publish activities.
    """

    message = "Only Pastors and Administrators may publish activities."


class IsActivityManager(IsPastorOrAdministrator):
    """
    Restrict activity management to Pastors and Administrators.
    """

    message = "Only Pastors and Administrators may manage activities."


class IsPublicOrActivityManager(BasePermission):
    """
    Allow public read access to published activities.
    Management access requires Pastor or Administrator.
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return IsPastorOrAdministrator().has_permission(
            request,
            view,
        )
