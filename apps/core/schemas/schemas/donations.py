from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from apps.core.schemas.schemas.base import BaseResponseSchema, BaseSchema
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod

class DonationBaseSchema(BaseSchema):
    """Base donation schema with common fields."""
    
    amount: Decimal
    transaction_id: Optional[str] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False
    recurring_frequency: Optional[str] = None
    donation_date: Optional[datetime] = None
    payment_method: PaymentMethod
    fund_type_id: Optional[int] = None

class DonationCreateSchema(DonationBaseSchema):
    """Schema for creating a new donation."""
    
    user_id: int
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate donation amount."""
        if v < Decimal('1.00'):
            raise ValueError("Donation amount must be at least $1.00")
        if v > Decimal('10000.00'):
            raise ValueError("Donation amount cannot exceed $10,000")
        return v
    
    @field_validator('recurring_frequency')
    @classmethod
    def validate_recurring(cls, v: Optional[str], info) -> Optional[str]:
        """Validate recurring donation frequency."""
        data = info.data
        if data.get('is_recurring') and not v:
            raise ValueError("Recurring donations require frequency")
        return v

class DonationUpdateSchema(DonationBaseSchema):
    """Schema for updating donation information."""
    
    amount: Optional[Decimal] = None
    transaction_id: Optional[str] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurring_frequency: Optional[str] = None
    status: Optional[DonationStatus] = None
    payment_method: Optional[PaymentMethod] = None
    fund_type_id: Optional[int] = None

class DonationResponseSchema(DonationBaseSchema, BaseResponseSchema):
    """Schema for donation response."""
    
    user_id: int
    status: DonationStatus = DonationStatus.PENDING
    user_name: Optional[str] = None
    fund_type_name: Optional[str] = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
    )

class FundTypeBaseSchema(BaseSchema):
    """Base fund type schema with common fields."""
    
    name: str
    description: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_balance: Decimal = Decimal('0.00')
    is_active: bool = True

class FundTypeCreateSchema(FundTypeBaseSchema):
    """Schema for creating a new fund type."""
    
    @field_validator('target_amount')
    @classmethod
    def validate_target_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate target amount."""
        if v and v < Decimal('0.00'):
            raise ValueError("Target amount cannot be negative")
        return v
    
    @field_validator('current_balance')
    @classmethod
    def validate_current_balance(cls, v: Decimal) -> Decimal:
        """Validate current balance."""
        if v < Decimal('0.00'):
            raise ValueError("Current balance cannot be negative")
        return v

class FundTypeUpdateSchema(BaseSchema):
    """Schema for updating fund type information."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    is_active: Optional[bool] = None

class FundTypeResponseSchema(FundTypeBaseSchema, BaseResponseSchema):
    """Schema for fund type response."""
    
    total_raised: Decimal = Decimal('0.00')
    progress_percentage: float = 0.0
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: str(v),
        }
    )
    
class DonationListResponseSchema(BaseSchema):
    """Schema for listing multiple donations with pagination support."""
    
    donations: List[DonationResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int

class FundTypeListResponseSchema(BaseSchema):
    """Schema for listing multiple fund types with pagination support."""
    
    fund_types: List[FundTypeResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int