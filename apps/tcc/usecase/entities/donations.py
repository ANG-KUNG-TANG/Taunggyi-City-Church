import html
from decimal import Decimal
from typing import Dict
from datetime import datetime
from apps.core.schemas.donations import DonationCreateSchema
from models.base.enums import DonationStatus, PaymentMethod

class DonationEntity:
    def __init__(self, donation_data: DonationCreateSchema):
        self.amount = donation_data.amount
        self.transaction_id = donation_data.transaction_id
        self.receipt_number = donation_data.receipt_number
        self.notes = donation_data.notes
        self.is_recurring = donation_data.is_recurring
        self.recurring_frequency = donation_data.recurring_frequency
        self.donation_date = donation_data.donation_date or datetime.now()
        self.payment_method = donation_data.payment_method
    
    def sanitize_inputs(self):
        """Sanitize donation content"""
        if self.transaction_id:
            self.transaction_id = html.escape(self.transaction_id.strip())
        if self.receipt_number:
            self.receipt_number = html.escape(self.receipt_number.strip())
        if self.notes:
            self.notes = html.escape(self.notes.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        # Business rules are now in schema validation
    
    def generate_receipt(self) -> Dict[str, str]:
        return {
            'receipt_number': self.receipt_number or 'N/A',
            'amount': str(self.amount),
            'date': self.donation_date.strftime('%Y-%m-%d %H:%M'),
            'payment_method': self.payment_method.value,
            'transaction_id': self.transaction_id or 'N/A'
        }

class FundTypeEntity:
    def __init__(self, fund_data: FundTypeCreateSchema):
        self.name = fund_data.name
        self.description = fund_data.description
        self.target_amount = fund_data.target_amount
        self.current_balance = fund_data.current_balance
    
    def sanitize_inputs(self):
        """Sanitize fund type content"""
        self.name = html.escape(self.name.strip())
        if self.description:
            self.description = html.escape(self.description.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        # Business rules are now in schema validation
    
    @property
    def total_raised(self) -> Decimal:
        return self.current_balance
    
    @property
    def progress_percentage(self) -> float:
        if not self.target_amount or self.target_amount == 0:
            return 0.0
        percentage = (float(self.total_raised) / float(self.target_amount)) * 100
        return min(100.0, percentage)