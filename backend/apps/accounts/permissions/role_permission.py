from rest_framework.permissions import BasePermission


class HasActiveRole(BasePermission):
    """
    Grant access only when the authenticated user has
    an active assignment to one of the allowed church roles.
    """

    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        if not self.allowed_roles:
            return False

        return user.role_assignments.filter(
            revoked_at__isnull=True,
            role__code__in=self.allowed_roles,
        ).exists()


class IsZoneLeader(HasActiveRole):
    allowed_roles = ("ZONE_LEADER",)


class IsPastor(HasActiveRole):
    allowed_roles = ("PASTOR",)


class IsAdministrator(HasActiveRole):
    allowed_roles = ("ADMINISTRATOR",)


class IsPastorOrAdministrator(HasActiveRole):
    allowed_roles = ("PASTOR", "ADMINISTRATOR")
