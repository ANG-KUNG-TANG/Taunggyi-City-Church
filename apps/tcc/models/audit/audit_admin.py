from apps.tcc import admin
from apps.tcc.models.base.auditlog import AuditLog
from apps.tcc.models.base.auditlog import SecurityEvent 


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'timestamp', 'ip_address']
    list_filter = ['action', 'resource_type', 'timestamp']
    search_fields = ['user__email', 'resource_type', 'ip_address']
    readonly_fields = ['timestamp']

