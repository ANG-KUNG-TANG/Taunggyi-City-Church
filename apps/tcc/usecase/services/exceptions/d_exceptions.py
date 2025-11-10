# donation_exceptions.py
from typing import Dict, List
from helpers.exceptions.domain.base_exception import BusinessException
from helpers.exceptions.domain.domain_exceptions import ObjectNotFoundException
from .error_codes import ErrorCode, Domain

class DonationException(BusinessException):
    def __init__(self, message: str, error_code: ErrorCode, details: Dict = None, user_message: str = None):
        super().__init__(
            message=message,
            error_code=error_code,
            domain=Domain.DONATION,
            status_code=400,
            details=details,
            user_message=user_message
        )

class DonationNotFoundException(ObjectNotFoundException):
    def __init__(self, donation_id: str = "", cause: Exception = None):
        super().__init__(
            model="Donation",
            lookup_params={"id": donation_id} if donation_id else {},
            domain=Domain.DONATION,
            cause=cause
        )

class DonationAmountInvalidException(DonationException):
    def __init__(self, amount: float, min_amount: float = 0.01, max_amount: float = 100000):
        super().__init__(
            message=f"Invalid donation amount: {amount}",
            error_code=ErrorCode.DONATION_AMOUNT_INVALID,
            details={
                "amount": amount,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "reason": "Amount outside valid range"
            },
            user_message=f"Donation amount must be between ${min_amount} and ${max_amount}"
        )

class DonationPaymentFailedException(DonationException):
    def __init__(self, donation_id: str, payment_method: str, reason: str, gateway_response: Dict = None):
        details = {
            "donation_id": donation_id,
            "payment_method": payment_method,
            "reason": reason
        }
        if gateway_response: details["gateway_response"] = gateway_response
            
        super().__init__(
            message=f"Payment failed for donation {donation_id}",
            error_code=ErrorCode.DONATION_PAYMENT_FAILED,
            details=details,
            user_message="Payment processing failed. Please try again or use a different payment method."
        )

class FundInactiveException(DonationException):
    def __init__(self, fund_id: str, fund_name: str):
        super().__init__(
            message=f"Fund {fund_name} is inactive",
            error_code=ErrorCode.FUND_INACTIVE,
            details={
                "fund_id": fund_id,
                "fund_name": fund_name,
                "reason": "Cannot donate to inactive fund"
            },
            user_message="This fund is currently not accepting donations."
        )

class TransactionDeclinedException(DonationException):
    def __init__(self, donation_id: str, decline_reason: str, gateway_code: str = None):
        details = {
            "donation_id": donation_id,
            "decline_reason": decline_reason
        }
        if gateway_code: details["gateway_code"] = gateway_code
            
        super().__init__(
            message=f"Transaction declined for donation {donation_id}",
            error_code=ErrorCode.TRANSACTION_DECLINED,
            details=details,
            user_message="Your transaction was declined. Please check your payment details."
        )

class RecurringDonationException(DonationException):
    def __init__(self, donation_id: str, operation: str, reason: str):
        super().__init__(
            message=f"Recurring donation {operation} failed for {donation_id}",
            error_code=ErrorCode.RECURRING_DONATION_ERROR,
            details={
                "donation_id": donation_id,
                "operation": operation,
                "reason": reason
            },
            user_message=f"Unable to {operation} recurring donation. Please try again."
        )

class DonationRefundException(DonationException):
    def __init__(self, donation_id: str, reason: str):
        super().__init__(
            message=f"Cannot refund donation {donation_id}",
            error_code=ErrorCode.DONATION_REFUND_ERROR,
            details={
                "donation_id": donation_id,
                "reason": reason
            },
            user_message="Unable to process refund. Please contact support."
        )

class ReceiptGenerationException(DonationException):
    def __init__(self, donation_id: str, reason: str):
        super().__init__(
            message=f"Receipt generation failed for donation {donation_id}",
            error_code=ErrorCode.RECEIPT_GENERATION_FAILED,
            details={
                "donation_id": donation_id,
                "reason": reason
            },
            user_message="Unable to generate receipt. Please try again."
        )

class PaymentMethodInvalidException(DonationException):
    def __init__(self, payment_method: str, allowed_methods: List[str]):
        super().__init__(
            message=f"Invalid payment method: {payment_method}",
            error_code=ErrorCode.PAYMENT_METHOD_INVALID,
            details={
                "payment_method": payment_method,
                "allowed_methods": allowed_methods,
                "reason": "Payment method not supported"
            },
            user_message=f"Payment method not supported. Allowed methods: {', '.join(allowed_methods)}"
        )

class FundTargetReachedException(DonationException):
    def __init__(self, fund_id: str, fund_name: str, target_amount: float):
        super().__init__(
            message=f"Fund {fund_name} target reached",
            error_code=ErrorCode.FUND_TARGET_REACHED,
            details={
                "fund_id": fund_id,
                "fund_name": fund_name,
                "target_amount": target_amount,
                "reason": "Fund has reached its target amount"
            },
            user_message="This fund has reached its target amount and is no longer accepting donations."
        )

class InsufficientFundsException(DonationException):
    def __init__(self, donation_id: str, payment_method: str, available_balance: float):
        super().__init__(
            message=f"Insufficient funds for donation {donation_id}",
            error_code=ErrorCode.INSUFFICIENT_FUNDS,
            details={
                "donation_id": donation_id,
                "payment_method": payment_method,
                "available_balance": available_balance,
                "reason": "Account has insufficient funds"
            },
            user_message="Insufficient funds. Please check your account balance."
        )