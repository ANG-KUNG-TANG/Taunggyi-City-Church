from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from .base import BaseResponseSchema
from common.pagination import PaginatedResponse
from apps.tcc.models.base.enums import DonationStatus, PaymentMethod


class DonationResponseSchema(BaseResponseSchema):
    user_id: int
    user_name: Optional[str] = None

    amount: str  # Decimal serialized as string
    transaction_id: Optional[str] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None

    is_recurring: bool = False
    recurring_frequency: Optional[str] = None
    donation_date: Optional[datetime] = None

    payment_method: PaymentMethod
    status: DonationStatus = DonationStatus.PENDING
    fund_type_id: Optional[int] = None
    fund_type_name: Optional[str] = None


class DonationListResponseSchema(PaginatedResponse[DonationResponseSchema]):
    total_raised_this_month: str = "0.00"
    total_donations_count: int = 0


class FundTypeResponseSchema(BaseResponseSchema):
    name: str
    description: Optional[str] = None
    target_amount: Optional[str] = None
    current_balance: str = "0.00"
    is_active: bool = True

    total_raised: str = "0.00"
    progress_percentage: float = 0.0


class FundTypeListResponseSchema(PaginatedResponse[FundTypeResponseSchema]):
    overall_total_raised: str = "0.00"
    active_funds: int = 0