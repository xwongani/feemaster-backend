import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from twilio.rest import Client as TwilioClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

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
            self.initialized = False
            logger.info("Notification service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during notification service cleanup: {e}")
    
    async def _initialize_email_client(self):
        """Initialize SendGrid email client"""
        try:
            self.email_client = SendGridAPIClient(settings.smtp_password)  # SendGrid API key
            logger.info("Email client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize email client: {e}")
    
    async def _initialize_sms_client(self):
        """Initialize Twilio SMS client"""
        try:
            self.sms_client = TwilioClient(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
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
        """Send email notification using SendGrid"""
        try:
            if not self.email_client:
                logger.warning("Email client not available")
                return False
            
            message = Mail(
                from_email=Email(settings.smtp_username),
                to_emails=To(notification.recipient_id),
                subject=notification.subject,
                html_content=Content("text/html", notification.message)
            )
            
            response = self.email_client.send(message)
            logger.info(f"Email sent to {notification.recipient_id}: {response.status_code}")
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _send_sms(self, notification: NotificationCreate) -> bool:
        """Send SMS notification using Twilio"""
        try:
            if not self.sms_client:
                logger.warning("SMS client not available")
                return False
            
            message = self.sms_client.messages.create(
                body=notification.message,
                from_=settings.twilio_phone_number,
                to=notification.recipient_id
            )
            
            logger.info(f"SMS sent to {notification.recipient_id}: {message.sid}")
            return message.status in ['queued', 'sent', 'delivered']
            
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
        """Send payment reminder with retry logic"""
        try:
            message = (
                f"Fee reminder: {student_data['first_name']} {student_data['last_name']} "
                f"has outstanding fees of K{amount_due:.2f} due on {due_date}. "
                "Please make payment to avoid late fees."
            )
            
            notification = NotificationCreate(
                recipient_type="parent",
                recipient_id=recipient_phone,
                channel=NotificationChannel.SMS,
                message=message,
                subject="Fee Payment Reminder"
            )
            
            # Try SMS first
            success = await self.send_notification(notification)
            
            # If SMS fails, try WhatsApp
            if not success and self.whatsapp_client:
                notification.channel = NotificationChannel.WHATSAPP
                success = await self.send_notification(notification)
            
            # If both fail, try email
            if not success and self.email_client and student_data.get('parent_email'):
                notification.channel = NotificationChannel.EMAIL
                notification.recipient_id = student_data['parent_email']
                success = await self.send_notification(notification)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send payment reminder: {e}")
            return False
    
    async def process_overdue_fees(self) -> Dict[str, int]:
        """Process overdue fees and send notifications"""
        try:
            # Get overdue fees
            overdue_query = """
                WITH overdue_fees AS (
                    SELECT 
                        sf.id,
                        sf.student_id,
                        sf.amount as amount_due,
                        sf.due_date,
                        s.first_name,
                        s.last_name,
                        p.phone as parent_phone,
                        p.email as parent_email,
                        COUNT(pr.id) as reminder_count
                    FROM student_fees sf
                    JOIN students s ON sf.student_id = s.id
                    JOIN parent_student_links psl ON s.id = psl.student_id
                    JOIN parents p ON psl.parent_id = p.id
                    LEFT JOIN payment_reminders pr ON sf.id = pr.student_fee_id
                    WHERE sf.is_paid = false 
                    AND sf.due_date < CURRENT_DATE
                    AND (pr.id IS NULL OR pr.created_at < CURRENT_DATE - INTERVAL '7 days')
                    GROUP BY sf.id, sf.student_id, sf.amount, sf.due_date, 
                             s.first_name, s.last_name, p.phone, p.email
                )
                SELECT * FROM overdue_fees
                WHERE reminder_count < 3;  -- Limit to 3 reminders
            """
            
            result = await db.execute_raw_query(overdue_query)
            
            if not result["success"]:
                return {"processed": 0, "failed": 0, "skipped": 0}
            
            overdue_fees = result["data"]
            stats = {"processed": 0, "failed": 0, "skipped": 0}
            
            for fee in overdue_fees:
                try:
                    # Check if parent has opted out of notifications
                    opt_out_query = """
                        SELECT is_enabled 
                        FROM parent_notification_preferences 
                        WHERE parent_id = (
                            SELECT parent_id 
                            FROM parent_student_links 
                            WHERE student_id = $1 
                            AND is_primary_contact = true
                        )
                        AND channel = 'sms';
                    """
                    
                    opt_out_result = await db.execute_raw_query(opt_out_query, [fee["student_id"]])
                    
                    if (opt_out_result["success"] and opt_out_result["data"] and 
                        not opt_out_result["data"][0]["is_enabled"]):
                        stats["skipped"] += 1
                        continue
                    
                    # Send reminder
                    success = await self.send_payment_reminder(
                        {
                            "first_name": fee["first_name"],
                            "last_name": fee["last_name"],
                            "parent_email": fee["parent_email"]
                        },
                        float(fee["amount_due"]),
                        fee["due_date"].strftime("%Y-%m-%d"),
                        fee["parent_phone"]
                    )
                    
                    if success:
                        # Record reminder
                        reminder_data = {
                            "student_fee_id": fee["id"],
                            "reminder_type": "overdue",
                            "channel": "sms",
                            "status": "sent"
                        }
                        
                        await db.execute_query("payment_reminders", "insert", data=reminder_data)
                        stats["processed"] += 1
                    else:
                        stats["failed"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process overdue fee {fee['id']}: {e}")
                    stats["failed"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to process overdue fees: {e}")
            return {"processed": 0, "failed": 0, "skipped": 0}
    
    async def schedule_overdue_reminders(self):
        """Schedule overdue fee reminders"""
        try:
            while True:
                # Process overdue fees
                stats = await self.process_overdue_fees()
                logger.info(f"Processed overdue fees: {stats}")
                
                # Wait for 24 hours before next run
                await asyncio.sleep(24 * 60 * 60)
                
        except Exception as e:
            logger.error(f"Overdue reminder scheduler failed: {e}")
            # Retry after 1 hour if failed
            await asyncio.sleep(60 * 60)
            await self.schedule_overdue_reminders()

# Create global notification service instance
notification_service = NotificationService() 