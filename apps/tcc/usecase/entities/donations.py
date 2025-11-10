from schemas.donations import DonationCreateSchema, FundTypeCreateSchema
import html
from decimal import Decimal
from typing import Dict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from models.base.enums import DonationStatus, PaymentMethod


class DonationEntity(DonationCreateSchema):
    def sanitize_inputs(self):
        """Sanitize donation content"""
        if self.transaction_id:
            self.transaction_id = html.escape(self.transaction_id.strip())
        if self.receipt_number:
            self.receipt_number = html.escape(self.receipt_number.strip())
        if self.notes:
            self.notes = html.escape(self.notes.strip())
    
    def validate_business_rules(self):
        """Donation-specific business rules"""
        # Minimum donation amount
        if self.amount < Decimal('1.00'):
            raise ValueError("Donation amount must be at least $1.00")
        
        # Maximum single donation amount
        if self.amount > Decimal('10000.00'):
            raise ValueError("Donation amount cannot exceed $10,000")
        
        # Recurring donations require frequency
        if self.is_recurring and not self.recurring_frequency:
            raise ValueError("Recurring donations require frequency")
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        self.validate_business_rules()
    
    def generate_receipt(self) -> Dict[str, str]:
        return {
            'receipt_number': self.receipt_number,
            'amount': str(self.amount),
            'date': self.donation_date.strftime('%Y-%m-%d %H:%M') if self.donation_date else 'N/A',
            'payment_method': self.payment_method.value,
            'transaction_id': self.transaction_id or 'N/A'
        }


class FundTypeEntity(FundTypeCreateSchema):
    def sanitize_inputs(self):
        """Sanitize fund type content"""
        self.name = html.escape(self.name.strip())
        if self.description:
            self.description = html.escape(self.description.strip())
    
    def validate_business_rules(self):
        """Fund type business rules"""
        # Target amount validation
        if self.target_amount and self.target_amount < Decimal('0.00'):
            raise ValueError("Target amount cannot be negative")
        
        # Current balance validation
        if self.current_balance < Decimal('0.00'):
            raise ValueError("Current balance cannot be negative")
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        self.validate_business_rules()
    
    @property
    def total_raised(self) -> Decimal:
        return self.current_balance
    
    @property
    def progress_percentage(self) -> float:
        if not self.target_amount or self.target_amount == 0:
            return 0.0
        percentage = (float(self.total_raised) / float(self.target_amount)) * 100
        return min(100.0, percentage)