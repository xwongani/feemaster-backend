# Optional imports for Twilio service
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Twilio not available - SMS service will be disabled")

from typing import List, Dict, Optional
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio not available - SMS service disabled")
            self.client = None
            self.from_number = None
            return
            
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = settings.twilio_phone_number

    async def send_sms(self, to_number: str, message: str) -> Dict:
        """Send a single SMS message"""
        try:
            if not TWILIO_AVAILABLE or not self.client:
                logger.warning("Twilio not available - cannot send SMS")
                return {
                    "success": False,
                    "error": "Twilio service not available"
                }
                
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status
            }
        except TwilioRestException as e:
            logger.error(f"Twilio error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_bulk_sms(self, recipients: List[Dict], message: str) -> Dict:
        """Send SMS to multiple recipients"""
        results = []
        for recipient in recipients:
            result = await self.send_sms(recipient["phone"], message)
            results.append({
                "recipient": recipient,
                "result": result
            })
        return {
            "success": True,
            "results": results
        }

    async def get_message_history(self, limit: int = 100) -> Dict:
        """Get message history from Twilio"""
        try:
            messages = self.client.messages.list(limit=limit)
            return {
                "success": True,
                "messages": [{
                    "sid": msg.sid,
                    "to": msg.to,
                    "from": msg.from_,
                    "body": msg.body,
                    "status": msg.status,
                    "date_sent": msg.date_sent,
                    "direction": msg.direction
                } for msg in messages]
            }
        except Exception as e:
            logger.error(f"Error fetching message history: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_recipient_groups(self) -> Dict:
        """Get predefined recipient groups (teachers, students, parents, staff)"""
        try:
            # Query database for different recipient groups
            query = """
                SELECT 
                    'teachers' as group_type,
                    json_agg(json_build_object(
                        'id', t.id,
                        'name', CONCAT(t.first_name, ' ', t.last_name),
                        'phone', t.phone
                    )) as recipients
                FROM teachers t
                WHERE t.phone IS NOT NULL
                UNION ALL
                SELECT 
                    'students' as group_type,
                    json_agg(json_build_object(
                        'id', s.id,
                        'name', CONCAT(s.first_name, ' ', s.last_name),
                        'phone', s.phone
                    )) as recipients
                FROM students s
                WHERE s.phone IS NOT NULL
                UNION ALL
                SELECT 
                    'parents' as group_type,
                    json_agg(json_build_object(
                        'id', p.id,
                        'name', CONCAT(p.first_name, ' ', p.last_name),
                        'phone', p.phone
                    )) as recipients
                FROM parents p
                WHERE p.phone IS NOT NULL
                UNION ALL
                SELECT 
                    'staff' as group_type,
                    json_agg(json_build_object(
                        'id', s.id,
                        'name', CONCAT(s.first_name, ' ', s.last_name),
                        'phone', s.phone
                    )) as recipients
                FROM staff s
                WHERE s.phone IS NOT NULL
            """
            result = await db.execute_raw_query(query)
            return {
                "success": True,
                "groups": result["data"]
            }
        except Exception as e:
            logger.error(f"Error fetching recipient groups: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 