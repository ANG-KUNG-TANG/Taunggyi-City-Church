"""
Announcement selectors for the Taunggyi City Church system.

Selectors provide read-only queries for announcement records.
Public queries must return published announcements only.
"""

from apps.announcements.models.announcement import Announcement


class AnnouncementSelector:
    """Read-only queries for announcements."""

    @staticmethod
    def get_announcement_by_id(announcement_id):
        """Retrieve one announcement by its UUID."""
        return Announcement.objects.filter(id=announcement_id).first()

    @staticmethod
    def get_published_announcements():
        """Return published announcements with their media prefetched."""
        return (
            Announcement.objects.filter(status=Announcement.Status.PUBLISHED)
            .prefetch_related("media")
            .order_by("-published_at", "-id")
        )

    @staticmethod
    def get_published_announcement_by_id(announcement_id):
        """Retrieve one published announcement with its media prefetched."""
        return (
            Announcement.objects.filter(
                id=announcement_id,
                status=Announcement.Status.PUBLISHED,
            )
            .prefetch_related("media")
            .first()
        )

    @staticmethod
    def get_all_announcements():
        """Return all announcements for authorised management views."""
        return Announcement.objects.all().order_by("-created_at", "-id")
