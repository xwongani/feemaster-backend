import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

from ..config import settings
from ..models import NotificationCreate, NotificationChannel

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.email_client = None
        self.sms_client = None
        self.whatsapp_client = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize notification service clients"""
        try:
            if settings.enable_notifications:
                # Initialize email client
                if settings.smtp_host:
                    await self._initialize_email_client()
                
                # Initialize SMS client
                if settings.twilio_account_sid:
                    await self._initialize_sms_client()
                
                # Initialize WhatsApp client
                if settings.whatsapp_api_url:
                    await self._initialize_whatsapp_client()
                
                self.initialized = True
                logger.info("Notification service initialized successfully")
            else:
                logger.info("Notifications disabled in settings")
                
        except Exception as e:
            logger.error(f"Failed to initialize notification service: {e}")
    
    async def cleanup(self):
        """Cleanup notification service resources"""
        try:
            if self.email_client:
                await self.email_client.quit()
            
            self.initialized = False
            logger.info("Notification service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during notification service cleanup: {e}")
    
    async def _initialize_email_client(self):
        """Initialize email client"""
        try:
            # Mock email client initialization
            # In production, use aiosmtplib or similar
            self.email_client = {
                "host": settings.smtp_host,
                "port": settings.smtp_port,
                "username": settings.smtp_username,
                "use_tls": settings.smtp_use_tls
            }
            logger.info("Email client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize email client: {e}")
    
    async def _initialize_sms_client(self):
        """Initialize SMS client"""
        try:
            # Mock SMS client initialization
            # In production, use Twilio SDK or other SMS provider
            self.sms_client = {
                "provider": settings.sms_provider,
                "account_sid": settings.twilio_account_sid,
                "auth_token": settings.twilio_auth_token,
                "phone_number": settings.twilio_phone_number
            }
            logger.info("SMS client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize SMS client: {e}")
    
    async def _initialize_whatsapp_client(self):
        """Initialize WhatsApp client"""
        try:
            # Mock WhatsApp client initialization
            # In production, use WhatsApp Business API
            self.whatsapp_client = {
                "api_url": settings.whatsapp_api_url,
                "api_key": settings.whatsapp_api_key,
                "phone_number": settings.whatsapp_phone_number
            }
            logger.info("WhatsApp client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp client: {e}")
    
    async def send_notification(self, notification: NotificationCreate) -> bool:
        """Send notification via specified channel"""
        try:
            if not self.initialized:
                logger.warning("Notification service not initialized")
                return False
            
            if notification.channel == NotificationChannel.EMAIL:
                return await self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                return await self._send_sms(notification)
            elif notification.channel == NotificationChannel.WHATSAPP:
                return await self._send_whatsapp(notification)
            else:
                logger.error(f"Unsupported notification channel: {notification.channel}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def _send_email(self, notification: NotificationCreate) -> bool:
        """Send email notification"""
        try:
            if not self.email_client:
                logger.warning("Email client not available")
                return False
            
            # Mock email sending
            # In production, implement actual email sending
            logger.info(f"Sending email to {notification.recipient_id}: {notification.subject}")
            
            # Simulate async email sending
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _send_sms(self, notification: NotificationCreate) -> bool:
        """Send SMS notification"""
        try:
            if not self.sms_client:
                logger.warning("SMS client not available")
                return False
            
            # Mock SMS sending
            # In production, implement actual SMS sending with Twilio or other provider
            logger.info(f"Sending SMS to {notification.recipient_id}: {notification.message}")
            
            # Simulate async SMS sending
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
    
    async def _send_whatsapp(self, notification: NotificationCreate) -> bool:
        """Send WhatsApp notification"""
        try:
            if not self.whatsapp_client:
                logger.warning("WhatsApp client not available")
                return False
            
            # Mock WhatsApp sending
            # In production, implement actual WhatsApp Business API calls
            logger.info(f"Sending WhatsApp to {notification.recipient_id}: {notification.message}")
            
            # Simulate async WhatsApp sending
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp: {e}")
            return False
    
    async def send_payment_confirmation(self, payment_data: Dict, recipient_phone: str, recipient_email: Optional[str] = None) -> Dict[str, bool]:
        """Send payment confirmation via multiple channels"""
        results = {}
        
        message = f"Payment received! Receipt: {payment_data['receipt_number']}, Amount: {payment_data['amount']}, Student: {payment_data['student_name']}"
        
        # Send SMS
        if recipient_phone:
            sms_notification = NotificationCreate(
                recipient_type="parent",
                recipient_id=recipient_phone,
                channel=NotificationChannel.SMS,
                message=message,
                subject="Payment Confirmation"
            )
            results["sms"] = await self.send_notification(sms_notification)
        
        # Send Email
        if recipient_email:
            email_notification = NotificationCreate(
                recipient_type="parent",
                recipient_id=recipient_email,
                channel=NotificationChannel.EMAIL,
                message=message,
                subject="Payment Confirmation - Fee Master Academy"
            )
            results["email"] = await self.send_notification(email_notification)
        
        return results
    
    async def send_payment_reminder(self, student_data: Dict, amount_due: float, due_date: str, recipient_phone: str) -> bool:
        """Send payment reminder"""
        message = f"Fee reminder: {student_data['first_name']} {student_data['last_name']} has outstanding fees of K{amount_due} due on {due_date}. Please make payment to avoid late fees."
        
        notification = NotificationCreate(
            recipient_type="parent",
            recipient_id=recipient_phone,
            channel=NotificationChannel.SMS,
            message=message,
            subject="Fee Payment Reminder"
        )
        
        return await self.send_notification(notification)
    
    async def send_bulk_notifications(self, notifications: List[NotificationCreate]) -> Dict[str, int]:
        """Send bulk notifications"""
        results = {"sent": 0, "failed": 0}
        
        for notification in notifications:
            success = await self.send_notification(notification)
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1
        
        return results

# Create global notification service instance
notification_service = NotificationService() 