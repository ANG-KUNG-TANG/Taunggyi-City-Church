from django.contrib import admin
from apps.tcc.models.audit.audit import AuditLog, SecurityEvent

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['timestamp']

@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'user', 'severity', 'timestamp', 'resolved']
    list_filter = ['event_type', 'severity', 'resolved', 'timestamp']
    search_fields = ['user__email', 'description']
    readonly_fields = ['timestamp']