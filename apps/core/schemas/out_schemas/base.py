from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Generic, TypeVar, List, Any, Dict
from decimal import Decimal
from enum import Enum

T = TypeVar('T')

class BaseOutputSchema(BaseModel):
    """Base schema for all output DTOs with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        },
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

class BaseResponseSchema(BaseOutputSchema):
    """Base response schema with common audit fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

class AuditMixin(BaseModel):
    """Mixin for audit fields."""
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    deleted_by: Optional[int] = None

class StatusMixin(BaseModel):
    """Mixin for status fields."""
    is_active: bool = True
    is_deleted: bool = False

class SimpleResponseSchema(BaseOutputSchema):
    """Simple response with basic information."""
    id: int
    name: str
    description: Optional[str] = None

class IDResponseSchema(BaseOutputSchema):
    """Response containing only ID."""
    id: int

class CountResponseSchema(BaseOutputSchema):
    """Response for count operations."""
    count: int
    entity: str

class StatusResponseSchema(BaseOutputSchema):
    """Status response schema."""
    status: str
    message: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class BulkOperationResponseSchema(BaseOutputSchema):
    """Response for bulk operations."""
    operation: str
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]] = []

class DeleteResponseSchema(BaseOutputSchema):
    """Response for delete operations."""
    id: int
    deleted: bool
    message: str = "Item deleted successfully"
    timestamp: datetime = Field(default_factory=datetime.now)

class RestoreResponseSchema(BaseOutputSchema):
    """Response for restore operations."""
    id: int
    restored: bool
    message: str = "Item restored successfully"
    timestamp: datetime = Field(default_factory=datetime.now)

class ToggleResponseSchema(BaseOutputSchema):
    """Response for toggle operations (active/inactive)."""
    id: int
    field: str
    old_value: bool
    new_value: bool
    message: str

class FileResponseSchema(BaseOutputSchema):
    """Response for file operations."""
    filename: str
    file_url: str
    file_size: int
    content_type: str
    checksum: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.now)

class ImageResponseSchema(FileResponseSchema):
    """Response for image operations."""
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    thumbnail_url: Optional[str] = None

class ExportResponseSchema(BaseOutputSchema):
    """Response for export operations."""
    export_id: str
    filename: str
    file_url: str
    format: str
    record_count: int
    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

class ImportResponseSchema(BaseOutputSchema):
    """Response for import operations."""
    import_id: str
    filename: str
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    errors: List[Dict[str, Any]] = []
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

class SearchResultSchema(BaseOutputSchema, Generic[T]):
    """Generic search result schema."""
    query: str
    results: List[T]
    total_count: int
    page: int
    total_pages: int
    search_duration: float

class LookupItemSchema(BaseOutputSchema):
    """Schema for lookup/dropdown items."""
    value: int
    label: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LookupResponseSchema(BaseOutputSchema):
    """Response for lookup operations."""
    items: List[LookupItemSchema]
    total: int

class OptionSchema(BaseOutputSchema):
    """Schema for select options."""
    value: str
    label: str
    disabled: bool = False
    group: Optional[str] = None

class EnumResponseSchema(BaseOutputSchema):
    """Response for enum values."""
    name: str
    value: str
    label: str
    description: Optional[str] = None

class HealthCheckSchema(BaseOutputSchema):
    """Health check response schema."""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    environment: str
    dependencies: Dict[str, str]

class SystemInfoSchema(BaseOutputSchema):
    """System information response."""
    name: str
    version: str
    environment: str
    debug: bool
    timezone: str
    current_time: datetime = Field(default_factory=datetime.now)
    features: Dict[str, bool]

class ErrorDetailSchema(BaseOutputSchema):
    """Detailed error information."""
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None

class ValidationErrorSchema(BaseOutputSchema):
    """Validation error response."""
    message: str = "Validation error"
    errors: List[ErrorDetailSchema]
    timestamp: datetime = Field(default_factory=datetime.now)

class PermissionSchema(BaseOutputSchema):
    """Permission response schema."""
    code: str
    name: str
    description: str
    category: str

class RoleSchema(BaseOutputSchema):
    """Role response schema."""
    id: int
    name: str
    description: str
    permissions: List[PermissionSchema]
    is_system: bool = False

class UserContextSchema(BaseOutputSchema):
    """User context for audit logs."""
    user_id: int
    username: str
    email: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuditLogSchema(BaseOutputSchema):
    """Audit log entry."""
    id: int
    action: str
    entity_type: str
    entity_id: int
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    context: UserContextSchema
    timestamp: datetime

class NotificationSchema(BaseOutputSchema):
    """Notification response."""
    id: int
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime

class DashboardStatsSchema(BaseOutputSchema):
    """Dashboard statistics."""
    total_users: int
    active_users: int
    new_users_today: int
    total_sermons: int
    upcoming_events: int
    prayer_requests: int
    recent_activity: List[Dict[str, Any]]

class ChartDataSchema(BaseOutputSchema):
    """Chart data response."""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    total: Optional[int] = None

class TimeRangeSchema(BaseOutputSchema):
    """Time range for reports."""
    start_date: datetime
    end_date: datetime
    timezone: str

class ReportResponseSchema(BaseOutputSchema):
    """Report response."""
    report_id: str
    name: str
    type: str
    data: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.now)
    time_range: Optional[TimeRangeSchema] = None

class SyncStatusSchema(BaseOutputSchema):
    """Synchronization status."""
    entity: str
    last_sync: Optional[datetime] = None
    total_records: int
    synced_records: int
    status: str  # pending, in_progress, completed, failed
    error_message: Optional[str] = None

class BackupStatusSchema(BaseOutputSchema):
    """Backup status response."""
    backup_id: str
    filename: str
    size: int
    status: str
    created_at: datetime
    expires_at: datetime

class SystemLogSchema(BaseOutputSchema):
    """System log entry."""
    id: int
    level: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger: str
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None