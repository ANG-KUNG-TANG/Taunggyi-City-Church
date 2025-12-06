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
        logger.debug(f"EmailService initialized with from_email: {self.from_email}")
    
    async def send_welcome_email(self, email: str, name: str) -> bool:
        """Send welcome email to new users"""
        try:
            subject = f"Welcome to Our Platform, {name}!"
            
            # Try to render template, fall back to plain text if template doesn't exist
            try:
                html_message = render_to_string('emails/welcome.html', {
                    'name': name,
                    'email': email,
                    'signup_date': datetime.now().strftime("%B %d, %Y")
                })
            except Exception as template_error:
                logger.warning(f"Template not found, using plain text: {template_error}")
                html_message = f"""
                <html>
                <body>
                    <h1>Welcome, {name}!</h1>
                    <p>Thank you for signing up with us.</p>
                    <p>Your email: {email}</p>
                    <p>Signup date: {datetime.now().strftime("%B %d, %Y")}</p>
                    <br>
                    <p>Best regards,<br>The Team</p>
                </body>
                </html>
                """
            
            plain_message = strip_tags(html_message)
            
            success = await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=True  # Don't raise exception on email failure
            )
            
            if success:
                logger.info(f"Welcome email sent to {email}")
                return True
            else:
                logger.warning(f"Failed to send welcome email to {email} (send_mail returned False)")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False
    
    async def send_password_reset_email(self, email: str, name: str, reset_link: str) -> bool:
        """Send password reset email"""
        try:
            subject = "Password Reset Request"
            
            # Try to render template, fall back to plain text
            try:
                html_message = render_to_string('emails/password_reset.html', {
                    'name': name,
                    'reset_link': reset_link,
                    'expiry_hours': 24
                })
            except Exception:
                html_message = f"""
                <html>
                <body>
                    <h1>Password Reset Request</h1>
                    <p>Hello {name},</p>
                    <p>You requested a password reset. Click the link below to reset your password:</p>
                    <p><a href="{reset_link}">{reset_link}</a></p>
                    <p>This link will expire in 24 hours.</p>
                    <br>
                    <p>If you didn't request this, please ignore this email.</p>
                </body>
                </html>
                """
            
            plain_message = strip_tags(html_message)
            
            success = await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=True
            )
            
            if success:
                logger.info(f"Password reset email sent to {email}")
                return True
            else:
                logger.warning(f"Failed to send password reset email to {email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    async def send_email_change_verification(self, email: str, name: str, verification_link: str) -> bool:
        """Send email change verification"""
        try:
            subject = "Confirm Your Email Change"
            
            # Try to render template, fall back to plain text
            try:
                html_message = render_to_string('emails/email_change.html', {
                    'name': name,
                    'verification_link': verification_link,
                    'new_email': email
                })
            except Exception:
                html_message = f"""
                <html>
                <body>
                    <h1>Confirm Email Change</h1>
                    <p>Hello {name},</p>
                    <p>Please confirm your email change by clicking the link below:</p>
                    <p><a href="{verification_link}">{verification_link}</a></p>
                    <br>
                    <p>If you didn't request this change, please contact support immediately.</p>
                </body>
                </html>
                """
            
            plain_message = strip_tags(html_message)
            
            success = await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=True
            )
            
            if success:
                logger.info(f"Email change verification sent to {email}")
                return True
            else:
                logger.warning(f"Failed to send email change verification to {email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email change verification to {email}: {str(e)}")
            return False
    
    async def send_account_status_change(self, email: str, name: str, new_status: str, reason: str = None) -> bool:
        """Notify user of account status change"""
        try:
            subject = f"Account Status Update: {new_status.title()}"
            
            # Try to render template, fall back to plain text
            try:
                html_message = render_to_string('emails/account_status.html', {
                    'name': name,
                    'new_status': new_status,
                    'reason': reason,
                    'change_date': datetime.now().strftime("%B %d, %Y %H:%M")
                })
            except Exception:
                html_message = f"""
                <html>
                <body>
                    <h1>Account Status Update</h1>
                    <p>Hello {name},</p>
                    <p>Your account status has been changed to: <strong>{new_status}</strong></p>
                    {f"<p>Reason: {reason}</p>" if reason else ""}
                    <p>Change date: {datetime.now().strftime("%B %d, %Y %H:%M")}</p>
                    <br>
                    <p>If you have any questions, please contact support.</p>
                </body>
                </html>
                """
            
            plain_message = strip_tags(html_message)
            
            success = await sync_to_async(send_mail)(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=self.from_email,
                recipient_list=[email],
                fail_silently=True
            )
            
            if success:
                logger.info(f"Account status change email sent to {email}")
                return True
            else:
                logger.warning(f"Failed to send account status email to {email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send account status email to {email}: {str(e)}")
            return False