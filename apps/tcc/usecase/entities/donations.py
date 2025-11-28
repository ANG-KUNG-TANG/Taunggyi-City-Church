from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime
from apps.core.schemas.input_schemas.donations import DonationCreateSchema, FundTypeCreateSchema

from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from .base_entity import BaseEntity


class DonationEntity(BaseEntity):
    def __init__(self, donation_data: DonationCreateSchema = None, **kwargs):
        super().__init__(**kwargs)
        
        if donation_data:
            self.amount = donation_data.amount
            self.transaction_id = donation_data.transaction_id
            self.receipt_number = donation_data.receipt_number
            self.notes = donation_data.notes
            self.is_recurring = donation_data.is_recurring
            self.recurring_frequency = donation_data.recurring_frequency
            self.donation_date = donation_data.donation_date or datetime.now()
            self.payment_method = donation_data.payment_method
            self.fund_type_id = donation_data.fund_type_id
            self.user_id = getattr(donation_data, 'user_id', None)
            self.status = getattr(donation_data, 'status', DonationStatus.PENDING)
        else:
            # For repository conversion
            self.amount = kwargs.get('amount')
            self.transaction_id = kwargs.get('transaction_id')
            self.receipt_number = kwargs.get('receipt_number')
            self.notes = kwargs.get('notes')
            self.is_recurring = kwargs.get('is_recurring', False)
            self.recurring_frequency = kwargs.get('recurring_frequency')
            self.donation_date = kwargs.get('donation_date', datetime.now())
            self.payment_method = kwargs.get('payment_method')
            self.fund_type_id = kwargs.get('fund_type_id')
            self.user_id = kwargs.get('user_id')
            self.status = kwargs.get('status', DonationStatus.PENDING)
    
    def sanitize_inputs(self):
        """Sanitize donation content"""
        self.transaction_id = self.sanitize_string(self.transaction_id)
        self.receipt_number = self.sanitize_string(self.receipt_number)
        self.notes = self.sanitize_string(self.notes)
    
    def prepare_for_persistence(self):
        """Prepare entity for database operations"""
        self.sanitize_inputs()
        self.update_timestamps()
    
    @classmethod
    def from_model(cls, model):
        """Create entity from Django model"""
        return cls(
            id=model.id,
            amount=model.amount,
            transaction_id=model.transaction_id,
            receipt_number=model.receipt_number,
            notes=model.notes,
            is_recurring=model.is_recurring,
            recurring_frequency=model.recurring_frequency,
            donation_date=model.donation_date,
            payment_method=model.payment_method,
            fund_type_id=model.fund_type_id,
            user_id=model.user_id,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def generate_receipt(self) -> Dict[str, str]:
        """Generate donation receipt"""
        return {
            'receipt_number': self.receipt_number or 'N/A',
            'amount': str(self.amount),
            'date': self.donation_date.strftime('%Y-%m-%d %H:%M'),
            'payment_method': self.payment_method.value if hasattr(self.payment_method, 'value') else str(self.payment_method),
            'transaction_id': self.transaction_id or 'N/A'
        }
    
    def validate_for_creation(self) -> list:
        """Validate donation for creation"""
        errors = self.validate_required_fields(['amount', 'payment_method', 'fund_type_id'])
        
        if self.amount is not None and self.amount <= Decimal('0.00'):
            errors.append("Amount must be greater than 0")
        
        if self.donation_date and self.donation_date > datetime.now():
            errors.append("Donation date cannot be in the future")
        
        return errors
    
    def is_successful(self) -> bool:
        """Check if donation was successful"""
        return self.status == DonationStatus.COMPLETED
    
    def __str__(self):
        return f"DonationEntity(id={self.id}, amount={self.amount}, status='{self.status}')"


class FundTypeEntity(BaseEntity):
    def __init__(self, fund_data: FundTypeCreateSchema = None, **kwargs):
        super().__init__(**kwargs)
        
        if fund_data:
            self.name = fund_data.name
            self.description = fund_data.description
            self.target_amount = fund_data.target_amount
            self.current_balance = fund_data.current_balance
            self.is_active = getattr(fund_data, 'is_active', True)
        else:
            # For repository conversion
            self.name = kwargs.get('name')
            self.description = kwargs.get('description')
            self.target_amount = kwargs.get('target_amount')
            self.current_balance = kwargs.get('current_balance', Decimal('0.00'))
            self.is_active = kwargs.get('is_active', True)
    
    def sanitize_inputs(self):
        """Sanitize fund type content"""
        self.name = self.sanitize_string(self.name)
        self.description = self.sanitize_string(self.description)
    
    def prepare_for_persistence(self):
        """Prepare entity for database operations"""
        self.sanitize_inputs()
        self.update_timestamps()
    
    @classmethod
    def from_model(cls, model):
        """Create entity from Django model"""
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            target_amount=model.target_amount,
            current_balance=model.current_balance,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @property
    def total_raised(self) -> Decimal:
        """Get total amount raised"""
        return self.current_balance
    
    @property
    def progress_percentage(self) -> float:
        """Calculate fundraising progress percentage"""
        if not self.target_amount or self.target_amount == 0:
            return 0.0
        percentage = (float(self.total_raised) / float(self.target_amount)) * 100
        return min(100.0, percentage)
    
    def is_target_reached(self) -> bool:
        """Check if fundraising target is reached"""
        return self.total_raised >= self.target_amount
    
    def validate_for_creation(self) -> list:
        """Validate fund type for creation"""
        errors = self.validate_required_fields(['name'])
        
        if self.target_amount is not None and self.target_amount < Decimal('0.00'):
            errors.append("Target amount cannot be negative")
        
        if self.current_balance is not None and self.current_balance < Decimal('0.00'):
            errors.append("Current balance cannot be negative")
        
        return errors
    
    def __str__(self):
        return f"FundTypeEntity(id={self.id}, name='{self.name}', target={self.target_amount})"