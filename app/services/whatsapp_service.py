import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.api_url = None
        self.api_key = None
        self.phone_number = None
        self.initialized = False
        self.session = None
        
    async def initialize(self):
        """Initialize WhatsApp Business API client"""
        try:
            if not settings.whatsapp_api_url or not settings.whatsapp_api_key:
                logger.warning("WhatsApp API credentials not configured")
                return
            
            self.api_url = settings.whatsapp_api_url
            self.api_key = settings.whatsapp_api_key
            self.phone_number = settings.whatsapp_phone_number
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            self.initialized = True
            logger.info("WhatsApp service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp service: {e}")
    
    async def cleanup(self):
        """Cleanup WhatsApp service resources"""
        try:
            if self.session:
                await self.session.close()
            self.initialized = False
            logger.info("WhatsApp service cleaned up")
        except Exception as e:
            logger.error(f"Error during WhatsApp service cleanup: {e}")
    
    async def send_message(self, to: str, message: str, message_type: str = "text") -> Dict:
        """Send WhatsApp message"""
        try:
            if not self.initialized:
                return {"success": False, "error": "WhatsApp service not initialized"}
            
            # Format phone number (remove + and add country code if needed)
            formatted_phone = self._format_phone_number(to)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": message_type
            }
            
            if message_type == "text":
                payload["text"] = {"body": message}
            elif message_type == "template":
                payload["template"] = message
            elif message_type == "document":
                payload["document"] = message
            
            async with self.session.post(
                f"{self.api_url}/messages",
                json=payload
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    # Log successful message
                    await self._log_message_sent(formatted_phone, message, "success")
                    return {
                        "success": True,
                        "message_id": result.get("messages", [{}])[0].get("id"),
                        "status": "sent"
                    }
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    await self._log_message_sent(formatted_phone, message, "error", error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status": "failed"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            await self._log_message_sent(to, message, "error", str(e))
            return {"success": False, "error": str(e)}
    
    async def send_template_message(self, to: str, template_name: str, language: str = "en", components: List[Dict] = None) -> Dict:
        """Send WhatsApp template message"""
        try:
            template_data = {
                "name": template_name,
                "language": {
                    "code": language
                }
            }
            
            if components:
                template_data["components"] = components
            
            return await self.send_message(to, template_data, "template")
            
        except Exception as e:
            logger.error(f"Failed to send template message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_payment_confirmation(self, phone: str, payment_data: Dict) -> Dict:
        """Send payment confirmation message"""
        try:
            message = (
                f"✅ Payment Confirmation\n\n"
                f"Receipt: {payment_data.get('receipt_number', 'N/A')}\n"
                f"Amount: K{payment_data.get('amount', 0):.2f}\n"
                f"Student: {payment_data.get('student_name', 'N/A')}\n"
                f"Date: {payment_data.get('payment_date', 'N/A')}\n"
                f"Method: {payment_data.get('payment_method', 'N/A')}\n\n"
                f"Thank you for your payment! 🎉"
            )
            
            return await self.send_message(phone, message)
            
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_payment_reminder(self, phone: str, student_data: Dict, amount_due: float, due_date: str) -> Dict:
        """Send payment reminder message"""
        try:
            message = (
                f"🔔 Fee Payment Reminder\n\n"
                f"Dear Parent/Guardian,\n\n"
                f"Student: {student_data.get('first_name', '')} {student_data.get('last_name', '')}\n"
                f"Grade: {student_data.get('grade', 'N/A')}\n"
                f"Amount Due: K{amount_due:.2f}\n"
                f"Due Date: {due_date}\n\n"
                f"Please make payment to avoid late fees.\n"
                f"Contact us if you have any questions.\n\n"
                f"Thank you! 📚"
            )
            
            return await self.send_message(phone, message)
            
        except Exception as e:
            logger.error(f"Failed to send payment reminder: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_bulk_message(self, recipients: List[str], message: str, message_type: str = "text") -> Dict:
        """Send bulk WhatsApp messages"""
        try:
            if not self.initialized:
                return {"success": False, "error": "WhatsApp service not initialized"}
            
            results = []
            successful = 0
            failed = 0
            
            # Send messages with rate limiting
            for i, recipient in enumerate(recipients):
                result = await self.send_message(recipient, message, message_type)
                results.append({
                    "recipient": recipient,
                    "success": result["success"],
                    "error": result.get("error")
                })
                
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
                
                # Rate limiting: wait 1 second between messages
                if i < len(recipients) - 1:
                    await asyncio.sleep(1)
            
            return {
                "success": True,
                "total": len(recipients),
                "successful": successful,
                "failed": failed,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk messages: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_document(self, to: str, document_url: str, caption: str = "") -> Dict:
        """Send WhatsApp document"""
        try:
            document_data = {
                "link": document_url,
                "caption": caption
            }
            
            return await self.send_message(to, document_data, "document")
            
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_message_status(self, message_id: str) -> Dict:
        """Get message delivery status"""
        try:
            if not self.initialized:
                return {"success": False, "error": "WhatsApp service not initialized"}
            
            async with self.session.get(f"{self.api_url}/messages/{message_id}") as response:
                result = await response.json()
                
                if response.status == 200:
                    return {
                        "success": True,
                        "status": result.get("status"),
                        "timestamp": result.get("timestamp")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", {}).get("message", "Unknown error")
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get message status: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_webhook_events(self) -> List[Dict]:
        """Get recent webhook events (for testing)"""
        try:
            # This would typically be handled by webhook endpoints
            # For now, return mock data
            return [
                {
                    "id": "mock_event_1",
                    "type": "message",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "from": "+260971234567",
                        "message": "Test message"
                    }
                }
            ]
        except Exception as e:
            logger.error(f"Failed to get webhook events: {e}")
            return []
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp API"""
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # If no country code, assume Zambia (+260)
        if not cleaned.startswith('+'):
            if cleaned.startswith('0'):
                cleaned = '+260' + cleaned[1:]
            else:
                cleaned = '+260' + cleaned
        
        return cleaned
    
    async def _log_message_sent(self, phone: str, message: str, status: str, error: str = None):
        """Log message sending activity"""
        try:
            await db.execute_query(
                "whatsapp_message_logs",
                "insert",
                data={
                    "phone_number": phone,
                    "message": message[:500],  # Truncate long messages
                    "status": status,
                    "error_message": error,
                    "sent_at": datetime.utcnow()
                }
            )
        except Exception as e:
            logger.error(f"Failed to log WhatsApp message: {e}")
    
    async def get_service_status(self) -> Dict:
        """Get WhatsApp service status"""
        return {
            "initialized": self.initialized,
            "api_url": self.api_url is not None,
            "phone_number": self.phone_number,
            "features": [
                "text_messages",
                "template_messages",
                "document_sharing",
                "bulk_messaging",
                "payment_confirmations",
                "payment_reminders"
            ]
        }

# Initialize service
whatsapp_service = WhatsAppService()
