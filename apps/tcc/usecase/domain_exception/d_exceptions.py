from typing import Dict, List, Optional, Any
from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException, DomainValidationException


class DonationException(BaseAppException):
    """Base exception for donation-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DONATION_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class DonationNotFoundException(EntityNotFoundException):
    """Exception when donation is not found."""
    
    def __init__(
        self,
        donation_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        if not user_message:
            user_message = "Donation record not found."
            
        super().__init__(
            entity_name="Donation",
            entity_id=donation_id,
            lookup_params=lookup_params or ({"id": donation_id} if donation_id else {}),
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class DonationAmountInvalidException(DomainValidationException):
    """Exception when donation amount is invalid."""
    
    def __init__(
        self,
        amount: float,
        min_amount: float = 0.01,
        max_amount: float = 100000,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "amount": amount,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "reason": "Amount outside valid range"
        })
        
        field_errors = {
            "amount": [f"Amount must be between ${min_amount:.2f} and ${max_amount:.2f}"]
        }
        
        if not user_message:
            user_message = f"Donation amount must be between ${min_amount:.2f} and ${max_amount:.2f}."
            
        super().__init__(
            message=f"Invalid donation amount: {amount}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class DonationPaymentFailedException(DonationException):
    """Exception when donation payment fails."""
    
    def __init__(
        self,
        donation_id: str,
        payment_method: str,
        reason: str,
        gateway_response: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "payment_method": payment_method,
            "reason": reason
        })
        if gateway_response:
            details["gateway_response"] = gateway_response
            
        if not user_message:
            user_message = "Payment processing failed. Please try again or use a different payment method."
            
        super().__init__(
            message=f"Payment failed for donation {donation_id}",
            error_code="DONATION_PAYMENT_FAILED",
            status_code=402,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class FundInactiveException(BusinessRuleException):
    """Exception when trying to donate to inactive fund."""
    
    def __init__(
        self,
        fund_id: str,
        fund_name: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "fund_id": fund_id,
            "fund_name": fund_name,
            "reason": "Cannot donate to inactive fund"
        })
        
        if not user_message:
            user_message = f"Fund '{fund_name}' is not currently accepting donations."
            
        super().__init__(
            rule_name="FUND_ACTIVE_REQUIRED",
            message=f"Fund {fund_name} is inactive",
            rule_description="Donations can only be made to active funds",
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class TransactionDeclinedException(DonationException):
    """Exception when transaction is declined by payment processor."""
    
    def __init__(
        self,
        donation_id: str,
        decline_reason: str,
        gateway_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "decline_reason": decline_reason
        })
        if gateway_code:
            details["gateway_code"] = gateway_code
            
        if not user_message:
            user_message = "Your transaction was declined. Please check your payment information and try again."
            
        super().__init__(
            message=f"Transaction declined for donation {donation_id}",
            error_code="TRANSACTION_DECLINED",
            status_code=402,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )