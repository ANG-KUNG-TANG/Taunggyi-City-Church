from django.core.exceptions import PermissionDenied

class PermissionMixin:
    """
    Provides DOMAIN permission handling.
    Models define their own can_create, can_view, can_edit, can_delete.
    """

    def _check_permission(self, user, obj, action):
        attr_check = f"check_can_{action}"
        attr_can   = f"can_{action}"

        # Strong permission (raises inside model)
        if hasattr(obj, attr_check):
            getattr(obj, attr_check)(user)
            return

        # Soft permission returning bool
        if hasattr(obj, attr_can):
            if not getattr(obj, attr_can)(user):
                raise PermissionDenied(f"You are not allowed to {action} this resource.")

        # No permission attribute → allow by default
        return
