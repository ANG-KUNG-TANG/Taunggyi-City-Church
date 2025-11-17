from apps.tcc.utils.audit_logging import AuditLogger

class AuditMixin:
    """
    Adds logging on CRUD operations.
    Domain repositories decide when to call these hooks.
    """

    def _log_create(self, user, obj, ip, ua):
        AuditLogger.log_create(user, obj, ip, ua)

    def _log_update(self, user, obj, changes, ip, ua):
        AuditLogger.log_update(user, obj, changes, ip, ua)

    def _log_delete(self, user, obj, ip, ua):
        AuditLogger.log_delete(user, obj, ip, ua)

    def _log_view(self, user, obj):
        AuditLogger.log_view(user, obj)
