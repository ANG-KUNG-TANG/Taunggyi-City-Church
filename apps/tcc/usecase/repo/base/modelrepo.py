
from apps.tcc.usecase.repo.base.audit_mixin import AuditMixin
from apps.tcc.usecase.repo.base.base_repo import BaseRepository
from apps.tcc.usecase.repo.base.permission_mixin import PermissionMixin
from apps.tcc.usecase.repo.base.soft_delete_mixin import SoftDeleteMixin


class DomainRepository(BaseRepository, PermissionMixin, AuditMixin, SoftDeleteMixin):
    """
    Foundation for domain repositories.
    Extends pure CRUD with:
        - permission checks
        - audit logging
        - soft delete
    """

    sensitive_models = ["User", "Donation", "PrayerRequest"]

    def _is_sensitive(self):
        return self.model_class.__name__ in self.sensitive_models

    def get_by_id(self, object_id, user, *args, **kwargs):
        obj = super().get_by_id(object_id)
        if not obj:
            return None

        self._check_permission(user, obj, "view")

        if self._is_sensitive():
            self._log_view(user, obj)

        return obj

    def create(self, data, user, request=None):
        temp_obj = self.model_class(**data)
        self._check_permission(user, temp_obj, "create")

        obj = super().create(data)

        self._log_create(user, obj,
                         request.META.get("REMOTE_ADDR") if request else None,
                         request.META.get("HTTP_USER_AGENT") if request else None)

        return obj

    def update(self, object_id, data, user, request=None):
        obj = self.get_by_id(object_id, user)
        self._check_permission(user, obj, "edit")

        old_values = {k: getattr(obj, k) for k in data.keys()}

        updated_obj = super().update(object_id, data)

        changes = {
            k: {"old": old_values[k], "new": data[k]}
            for k in data
        }

        self._log_update(user, updated_obj,
                         changes,
                         request.META.get("REMOTE_ADDR") if request else None,
                         request.META.get("HTTP_USER_AGENT") if request else None)

        return updated_obj

    def delete(self, object_id, user, request=None):
        obj = self.get_by_id(object_id, user)
        self._check_permission(user, obj, "delete")

        self._log_delete(
            user,
            obj,
            request.META.get("REMOTE_ADDR") if request else None,
            request.META.get("HTTP_USER_AGENT") if request else None
        )

        self._soft_delete(obj, user)
        return True
