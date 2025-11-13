from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class StatusResponse(BaseModel):
    """Simple status response schema."""
    
    status: str
    message: str
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

class CountResponse(BaseModel):
    """Count response schema."""
    
    count: int
    entity: str

class BulkOperation(BaseModel):
    """Schema for bulk operations."""
    
    ids: List[int]
    operation: str
    data: Optional[Any] = None

class FileUploadResponse(BaseModel):
    """File upload response schema."""
    
    filename: str
    file_url: str
    file_size: int
    content_type: str

class SearchResponse(BaseModel):
    """Search response schema."""
    
    query: str
    results: List[Any]
    total_count: int

class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    status: str
    timestamp: datetime
    version: str
    database: bool
    cache: bool
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)