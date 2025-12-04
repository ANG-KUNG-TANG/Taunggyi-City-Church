from typing import Dict, Any, List, Optional
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from asgiref.sync import sync_to_async
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending various email notifications"""
    
    def __init__(self, from_email: str = None):
        self.from_email = from_email or "noreply@yourdomain.com"
    
    async def send_welcome_email(self, email: str, name: str) -> bool:
        """Send welcome email to new users"""
        try:
            subject = f"Welcome to Our Platform, {name}!"
            
            html_message = render_to_string('emails/welcome.html', {
                'name': name,
                'email': email,
                'signup_date': datetime.now().strftime("%B %d, %Y")
            })
            
            plain_message = strip_tags(html_message)
            
            await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=False
            )
            
            logger.info(f"Welcome email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False
    
    async def send_password_reset_email(self, email: str, name: str, reset_link: str) -> bool:
        """Send password reset email"""
        try:
            subject = "Password Reset Request"
            
            html_message = render_to_string('emails/password_reset.html', {
                'name': name,
                'reset_link': reset_link,
                'expiry_hours': 24  # Token expires in 24 hours
            })
            
            plain_message = strip_tags(html_message)
            
            await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=False
            )
            
            logger.info(f"Password reset email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    async def send_email_change_verification(self, email: str, name: str, verification_link: str) -> bool:
        """Send email change verification"""
        try:
            subject = "Confirm Your Email Change"
            
            html_message = render_to_string('emails/email_change.html', {
                'name': name,
                'verification_link': verification_link,
                'new_email': email
            })
            
            plain_message = strip_tags(html_message)
            
            await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=False
            )
            
            logger.info(f"Email change verification sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email change verification to {email}: {str(e)}")
            return False
    
    async def send_account_status_change(self, email: str, name: str, new_status: str, reason: str = None) -> bool:
        """Notify user of account status change"""
        try:
            subject = f"Account Status Update: {new_status.title()}"
            
            html_message = render_to_string('emails/account_status.html', {
                'name': name,
                'new_status': new_status,
                'reason': reason,
                'change_date': datetime.now().strftime("%B %d, %Y %H:%M")
            })
            
            plain_message = strip_tags(html_message)
            
            await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=False
            )
            
            logger.info(f"Account status change email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send account status email to {email}: {str(e)}")
            return False