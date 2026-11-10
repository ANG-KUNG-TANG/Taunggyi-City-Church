"""
Activity selectors for the Taunggyi City Church system.

Selectors provide read-only queries for activity records.
Public queries must return published activities only.
"""

from apps.activities.models.activity import Activity


class ActivitySelector:
    """Read-only queries for activities."""

    @staticmethod
    def get_activity_by_id(activity_id):
        """Retrieve one activity by its UUID."""
        return Activity.objects.filter(id=activity_id).first()

    @staticmethod
    def get_published_activities():
        """Return published activities for public access."""
        return Activity.objects.filter(status=Activity.Status.PUBLISHED).order_by(
            "-published_at"
        )

    @staticmethod
    def get_published_activity_by_id(activity_id):
        """Retrieve one published activity for public access."""
        return Activity.objects.filter(
            id=activity_id,
            status=Activity.Status.PUBLISHED,
        ).first()

    @staticmethod
    def get_all_activities():
        """Return all activities for authorized management views."""
        return Activity.objects.all().order_by("-created_at")
