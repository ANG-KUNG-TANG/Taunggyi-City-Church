from datetime import datetime
from apps.tcc.models.base.base_model import BaseModel
from django.db import models

from apps.tcc.models.base.enums import DonationStatus, PaymentMethod
from apps.tcc.models.users.users import User

class FundType(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    target_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Fundraising target"
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Current fund balance"
    )
    
    class Meta:
        db_table = "fund_types"
        verbose_name = "Fund Type"
        verbose_name_plural = "Fund Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def total_raised(self):
        return self.donations.filter(status=DonationStatus.COMPLETED).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
    
    @property
    def progress_percentage(self):
        if not self.target_amount:
            return 0
        return min(100, (self.total_raised / self.target_amount) * 100)


class Donation(BaseModel):
    donor = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='donations'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Donation amount"
    )
    donation_date = models.DateTimeField(default=datetime.now())
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    fund = models.ForeignKey(
        FundType,
        on_delete=models.PROTECT,
        related_name='donations'
    )
    
    is_recurring = models.BooleanField(
        default=False,
        help_text="Is this a recurring donation?"
    )
    recurring_frequency = models.CharField(
        max_length=20,
        choices=[
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly'),
            ('YEARLY', 'Yearly'),
        ],
        blank=True,
        help_text="Frequency for recurring donations"
    )
    
    status = models.CharField(
        max_length=20,
        choices=DonationStatus.choices,
        default=DonationStatus.PENDING
    )
    
    transaction_id = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Payment gateway transaction ID"
    )
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Donation receipt number"
    )
    notes = models.TextField(blank=True, help_text="Additional notes")
    
    class Meta:
        db_table = "donations"
        verbose_name = "Donation"
        verbose_name_plural = "Donations"
        ordering = ['-donation_date']
        indexes = [
            models.Index(fields=['donation_date', 'status']),
            models.Index(fields=['donor', 'donation_date']),
            models.Index(fields=['fund', 'status']),
        ]
    
    def __str__(self):
        return f"{self.donor.name} - ${self.amount} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number and self.status == DonationStatus.COMPLETED:
            self.receipt_number = f"RCP-{self.id}"
        super().save(*args, **kwargs)
    
    def process_payment(self):
        """Simulate payment processing"""
        if self.status == DonationStatus.COMPLETED:
            return True
            
        try:
            # Payment processing logic would go here
            self.status = DonationStatus.COMPLETED
            self.save()
            
            # Update fund balance
            self.fund.current_balance += self.amount
            self.fund.save()
            
            return True
        except Exception:
            self.status = DonationStatus.FAILED
            self.save()
            return False
    
    def generate_receipt(self):
        """Generate donation receipt data"""
        return {
            'receipt_number': self.receipt_number,
            'donor_name': self.donor.name,
            'donor_email': self.donor.email,
            'amount': self.amount,
            'date': self.donation_date.strftime('%Y-%m-%d %H:%M'),
            'fund': self.fund.name,
            'payment_method': self.get_payment_method_display(),
            'transaction_id': self.transaction_id or 'N/A'
        }

