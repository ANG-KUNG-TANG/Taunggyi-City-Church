from pyexpat import model
from django.contrib.auth import get_user_model

User = get_user_model()


class PermissionMixin(model.Model):
    """
    Adds permission methods: can_view, can_edit, can_delete
    Requires: created_by (from AuditMixin) or override
    """

    class Meta:
        abstract = True

    def can_view(self, user):
        """Can user view this object?"""
        if not user or not user.is_authenticated:
            return False

        # Admin sees all
        if getattr(user, 'is_admin', False) or user.is_superuser:
            return True

        # Owner can view
        if hasattr(self, 'created_by') and self.created_by == user:
            return True

        # Zone leader logic (if ZoneMixin used)
        if hasattr(self, 'is_zone_leader'):
            return self.is_zone_leader(user)

        return False

    def can_edit(self, user):
        """Can user edit this object?"""
        if not self.can_view(user):
            return False

        # Only active records can be edited
        if hasattr(self, 'is_active') and not self.is_active:
            return False

        # Owner can edit
        if hasattr(self, 'created_by') and self.created_by == user:
            return True

        # Zone leader can edit
        if hasattr(self, 'is_zone_leader'):
            return self.is_zone_leader(user)

        return False

    def can_delete(self, user):
        """Can user delete this object?"""
        return self.can_edit(user)