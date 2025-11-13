from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import Field, field_validator
from .base import BaseSchema
from models.base.enums import DonationStatus, PaymentMethod


class FundTypeBaseSchema(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    target_amount: Optional[Decimal] = Field(None, ge=0)
    current_balance: Decimal = Field(default=0, ge=0)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return v.strip()


class FundTypeCreateSchema(FundTypeBaseSchema):
    pass


class FundTypeUpdateSchema(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    target_amount: Optional[Decimal] = Field(None, ge=0)
    current_balance: Optional[Decimal] = Field(None, ge=0)


class FundTypeResponseSchema(FundTypeBaseSchema):
    total_raised: Decimal = Field(default=0)
    progress_percentage: float = Field(default=0, ge=0, le=100)


class DonationBaseSchema(BaseSchema):
    amount: Decimal = Field(..., gt=0)
    donation_date: datetime = Field(default_factory=datetime.now)
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH)
    is_recurring: bool = Field(default=False)
    recurring_frequency: Optional[str] = None
    status: DonationStatus = Field(default=DonationStatus.PENDING)
    transaction_id: Optional[str] = Field(None, max_length=100)
    receipt_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class DonationCreateSchema(DonationBaseSchema):
    donor_id: int = Field(...)
    fund_id: int = Field(...)


class DonationUpdateSchema(BaseSchema):
    amount: Optional[Decimal] = Field(None, gt=0)
    donation_date: Optional[datetime] = None
    payment_method: Optional[PaymentMethod] = None
    fund_id: Optional[int] = None
    is_recurring: Optional[bool] = None
    recurring_frequency: Optional[str] = None
    status: Optional[DonationStatus] = None
    transaction_id: Optional[str] = Field(None, max_length=100)
    receipt_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class DonationResponseSchema(DonationBaseSchema):
    donor_id: int
    fund_id: int