from pydantic import BaseModel, field_validator
from typing import Generic, TypeVar, List
from math import ceil

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    
    page: int = 1
    page_size: int = 20
    
    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        """Validate page number."""
        if v < 1:
            raise ValueError("Page must be greater than 0")
        return v
    
    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Validate page size."""
        if v < 1 or v > 100:
            raise ValueError("Page size must be between 1 and 100")
        return v
    
    @property
    def skip(self) -> int:
        """Calculate number of records to skip."""
        return (self.page - 1) * self.page_size

class PaginatedResponse(BaseModel, Generic[T]):
    """Schema for paginated response."""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> 'PaginatedResponse[T]':
        """Create a paginated response."""
        total_pages = ceil(total / params.page_size) if total > 0 else 1
        
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )