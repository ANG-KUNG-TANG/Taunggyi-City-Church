"""
Announcement permissions for the Taunggyi City Church system.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions.role_permission import (
    IsPastorOrAdministrator,
)


class CanPublishAnnouncement(IsPastorOrAdministrator):
    """
    Only active Pastors and Administrators may publish announcements.
    """

    message = "Only Pastors and Administrators may publish announcements."


class IsAnnouncementManager(IsPastorOrAdministrator):
    """
    Restrict announcement management to Pastors and Administrators.
    """

    message = "Only Pastors and Administrators may manage announcements."


class IsPublicOrAnnouncementManager(BasePermission):
    """
    Allow public read access to published announcements.
    Management access requires Pastor or Administrator.
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return IsPastorOrAdministrator().has_permission(
            request,
            view,
        )
