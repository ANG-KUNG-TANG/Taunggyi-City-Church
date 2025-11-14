from typing import Any, Dict, List, Optional

from apps.core.core_exceptions.base import BaseAppException, ErrorContext
from apps.core.core_exceptions.domain import BusinessRuleException, EntityNotFoundException, ValidationException

class DonationException(BaseAppException):
    """Base exception for donation-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DONATION_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class DonationNotFoundException(EntityNotFoundException):
    def __init__(
        self,
        donation_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            entity_name="Donation",
            entity_id=donation_id,
            lookup_params=lookup_params or ({"id": donation_id} if donation_id else {}),
            details=details,
            context=context,
            cause=cause
        )


class DonationAmountInvalidException(ValidationException):
    def __init__(
        self,
        amount: float,
        min_amount: float = 0.01,
        max_amount: float = 100000,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "amount": amount,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "reason": "Amount outside valid range"
        })
        
        field_errors = {
            "amount": [f"Amount must be between ${min_amount} and ${max_amount}"]
        }
        
        super().__init__(
            message=f"Invalid donation amount: {amount}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class DonationPaymentFailedException(DonationException):
    def __init__(
        self,
        donation_id: str,
        payment_method: str,
        reason: str,
        gateway_response: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "payment_method": payment_method,
            "reason": reason
        })
        if gateway_response:
            details["gateway_response"] = gateway_response
            
        super().__init__(
            message=f"Payment failed for donation {donation_id}",
            error_code="DONATION_PAYMENT_FAILED",
            status_code=402,
            details=details,
            context=context,
            cause=cause
        )


class FundInactiveException(BusinessRuleException):
    def __init__(
        self,
        fund_id: str,
        fund_name: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "fund_id": fund_id,
            "fund_name": fund_name,
            "reason": "Cannot donate to inactive fund"
        })
            
        super().__init__(
            rule_name="FUND_ACTIVE_REQUIRED",
            message=f"Fund {fund_name} is inactive",
            rule_description="Donations can only be made to active funds",
            details=details,
            context=context,
            cause=cause
        )


class TransactionDeclinedException(DonationException):
    def __init__(
        self,
        donation_id: str,
        decline_reason: str,
        gateway_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "decline_reason": decline_reason
        })
        if gateway_code:
            details["gateway_code"] = gateway_code
            
        super().__init__(
            message=f"Transaction declined for donation {donation_id}",
            error_code="TRANSACTION_DECLINED",
            status_code=402,
            details=details,
            context=context,
            cause=cause
        )


class RecurringDonationException(DonationException):
    def __init__(
        self,
        donation_id: str,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "operation": operation,
            "reason": reason
        })
            
        super().__init__(
            message=f"Recurring donation {operation} failed for {donation_id}",
            error_code="RECURRING_DONATION_ERROR",
            status_code=400,
            details=details,
            context=context,
            cause=cause
        )


class DonationRefundException(DonationException):
    def __init__(
        self,
        donation_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "reason": reason
        })
            
        super().__init__(
            message=f"Cannot refund donation {donation_id}",
            error_code="DONATION_REFUND_ERROR",
            status_code=400,
            details=details,
            context=context,
            cause=cause
        )


class ReceiptGenerationException(DonationException):
    def __init__(
        self,
        donation_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "reason": reason
        })
            
        super().__init__(
            message=f"Receipt generation failed for donation {donation_id}",
            error_code="RECEIPT_GENERATION_FAILED",
            status_code=400,
            details=details,
            context=context,
            cause=cause
        )


class PaymentMethodInvalidException(ValidationException):
    def __init__(
        self,
        payment_method: str,
        allowed_methods: List[str],
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "payment_method": payment_method,
            "allowed_methods": allowed_methods,
            "reason": "Payment method not supported"
        })
        
        field_errors = {
            "payment_method": [f"Payment method not supported. Allowed methods: {', '.join(allowed_methods)}"]
        }
            
        super().__init__(
            message=f"Invalid payment method: {payment_method}",
            field_errors=field_errors,
            details=details,
            context=context,
            cause=cause
        )


class FundTargetReachedException(BusinessRuleException):
    def __init__(
        self,
        fund_id: str,
        fund_name: str,
        target_amount: float,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "fund_id": fund_id,
            "fund_name": fund_name,
            "target_amount": target_amount,
            "reason": "Fund has reached its target amount"
        })
            
        super().__init__(
            rule_name="FUND_TARGET_NOT_REACHED",
            message=f"Fund {fund_name} target reached",
            rule_description="Donations cannot be made to funds that have reached their target amount",
            details=details,
            context=context,
            cause=cause
        )


class InsufficientFundsException(DonationException):
    def __init__(
        self,
        donation_id: str,
        payment_method: str,
        available_balance: float,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "donation_id": donation_id,
            "payment_method": payment_method,
            "available_balance": available_balance,
            "reason": "Account has insufficient funds"
        })
            
        super().__init__(
            message=f"Insufficient funds for donation {donation_id}",
            error_code="INSUFFICIENT_FUNDS",
            status_code=402,
            details=details,
            context=context,
            cause=cause
        )