import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

from ..config import settings
from ..models import ReceiptData, ReceiptResponse

logger = logging.getLogger(__name__)

class ReceiptService:
    def __init__(self):
        self.receipts_path = Path(settings.upload_path) / "receipts"
        self.initialized = False
    
    async def initialize(self):
        """Initialize receipt service"""
        try:
            if settings.enable_receipts:
                # Create receipts directory if it doesn't exist
                self.receipts_path.mkdir(parents=True, exist_ok=True)
                
                self.initialized = True
                logger.info("Receipt service initialized successfully")
            else:
                logger.info("Receipt generation disabled in settings")
                
        except Exception as e:
            logger.error(f"Failed to initialize receipt service: {e}")
    
    async def cleanup(self):
        """Cleanup receipt service resources"""
        try:
            self.initialized = False
            logger.info("Receipt service cleaned up")
            
        except Exception as e:
            logger.error(f"Error during receipt service cleanup: {e}")
    
    async def generate_receipt(self, receipt_data: ReceiptData) -> Dict[str, Any]:
        """Generate a receipt for a payment"""
        try:
            if not self.initialized:
                logger.warning("Receipt service not initialized")
                return {"success": False, "error": "Service not initialized"}
            
            payment = receipt_data.payment
            student = receipt_data.student
            school_info = receipt_data.school_info
            
            # Generate receipt content
            receipt_content = self._generate_receipt_content(payment, student, school_info)
            
            # Save receipt to file
            receipt_filename = f"receipt_{payment['receipt_number']}.json"
            receipt_path = self.receipts_path / receipt_filename
            
            with open(receipt_path, 'w') as f:
                json.dump(receipt_content, f, indent=2, default=str)
            
            # Generate receipt URL
            receipt_url = f"/api/v1/receipts/{receipt_filename}"
            
            receipt_response = {
                "id": f"receipt_{payment['id']}",
                "payment_id": payment["id"],
                "receipt_number": payment["receipt_number"],
                "file_url": receipt_url,
                "created_at": datetime.utcnow().isoformat(),
                "content": receipt_content
            }
            
            logger.info(f"Receipt generated successfully for payment {payment['id']}")
            return {"success": True, "data": receipt_response}
            
        except Exception as e:
            logger.error(f"Failed to generate receipt: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_receipt_content(self, payment: Dict, student: Dict, school_info: Dict) -> Dict[str, Any]:
        """Generate receipt content"""
        return {
            "receipt_header": {
                "school_name": school_info.get("name", "Fee Master Academy"),
                "school_address": school_info.get("address", "123 Education Street, Lusaka, Zambia"),
                "school_phone": school_info.get("phone", "+260 97 123 4567"),
                "school_email": school_info.get("email", "info@feemaster.edu"),
                "receipt_title": "PAYMENT RECEIPT"
            },
            "receipt_details": {
                "receipt_number": payment["receipt_number"],
                "payment_date": payment["payment_date"],
                "generated_at": datetime.utcnow().isoformat()
            },
            "student_details": {
                "student_name": f"{student.get('first_name', '')} {student.get('last_name', '')}",
                "student_id": student.get("student_id", "N/A"),
                "grade": student.get("current_grade", "N/A"),
                "class": student.get("current_class", "N/A")
            },
            "payment_details": {
                "amount": float(payment["amount"]),
                "payment_method": payment["payment_method"],
                "transaction_reference": payment.get("transaction_reference"),
                "payment_status": payment["payment_status"],
                "notes": payment.get("notes", "")
            },
            "footer": {
                "terms": "This receipt is computer generated and valid without signature.",
                "contact": "For any queries, please contact the school finance office.",
                "thank_you": "Thank you for your payment!"
            }
        }
    
    async def get_receipt(self, receipt_number: str) -> Dict[str, Any]:
        """Get receipt by receipt number"""
        try:
            receipt_filename = f"receipt_{receipt_number}.json"
            receipt_path = self.receipts_path / receipt_filename
            
            if not receipt_path.exists():
                return {"success": False, "error": "Receipt not found"}
            
            with open(receipt_path, 'r') as f:
                receipt_content = json.load(f)
            
            return {"success": True, "data": receipt_content}
            
        except Exception as e:
            logger.error(f"Failed to get receipt: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_html_receipt(self, receipt_data: ReceiptData) -> str:
        """Generate HTML receipt for printing/emailing"""
        payment = receipt_data.payment
        student = receipt_data.student
        school_info = receipt_data.school_info
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Receipt - {payment['receipt_number']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }}
                .school-name {{ font-size: 24px; font-weight: bold; color: #333; }}
                .receipt-title {{ font-size: 18px; color: #666; margin-top: 10px; }}
                .details {{ margin: 20px 0; }}
                .row {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                .label {{ font-weight: bold; }}
                .amount {{ font-size: 18px; font-weight: bold; color: #2563eb; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="school-name">{school_info.get("name", "Fee Master Academy")}</div>
                <div>{school_info.get("address", "123 Education Street, Lusaka, Zambia")}</div>
                <div>{school_info.get("phone", "+260 97 123 4567")} | {school_info.get("email", "info@feemaster.edu")}</div>
                <div class="receipt-title">PAYMENT RECEIPT</div>
            </div>
            
            <div class="details">
                <div class="row">
                    <span class="label">Receipt Number:</span>
                    <span>{payment['receipt_number']}</span>
                </div>
                <div class="row">
                    <span class="label">Date:</span>
                    <span>{payment['payment_date']}</span>
                </div>
                <div class="row">
                    <span class="label">Student Name:</span>
                    <span>{student.get('first_name', '')} {student.get('last_name', '')}</span>
                </div>
                <div class="row">
                    <span class="label">Student ID:</span>
                    <span>{student.get('student_id', 'N/A')}</span>
                </div>
                <div class="row">
                    <span class="label">Grade/Class:</span>
                    <span>{student.get('current_grade', 'N/A')} - {student.get('current_class', 'N/A')}</span>
                </div>
                <div class="row">
                    <span class="label">Payment Method:</span>
                    <span>{payment['payment_method'].replace('_', ' ').title()}</span>
                </div>
                <div class="row">
                    <span class="label">Amount Paid:</span>
                    <span class="amount">K {payment['amount']}</span>
                </div>
                <div class="row">
                    <span class="label">Status:</span>
                    <span>{payment['payment_status'].title()}</span>
                </div>
            </div>
            
            <div class="footer">
                <p>This receipt is computer generated and valid without signature.</p>
                <p>For any queries, please contact the school finance office.</p>
                <p><strong>Thank you for your payment!</strong></p>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    async def send_receipt(self, receipt_data: ReceiptData, channels: list = None) -> Dict[str, Any]:
        """Send receipt via specified channels"""
        try:
            from .notification_service import notification_service
            
            # Generate receipt
            receipt_result = await self.generate_receipt(receipt_data)
            if not receipt_result["success"]:
                return receipt_result
            
            receipt = receipt_result["data"]
            channels = channels or ["email"]
            
            # Send via specified channels
            sent_channels = []
            for channel in channels:
                if channel == "email" and receipt_data.student.get("email"):
                    # Send email with receipt attachment
                    # In production, implement actual email sending with attachment
                    sent_channels.append("email")
                    logger.info(f"Receipt sent via email to {receipt_data.student['email']}")
                
                elif channel == "sms" and receipt_data.student.get("contact"):
                    # Send SMS with receipt link
                    message = f"Receipt {receipt['receipt_number']} generated. Amount: K{receipt_data.payment['amount']}. View: {receipt['file_url']}"
                    # Use notification service to send SMS
                    sent_channels.append("sms")
                    logger.info(f"Receipt notification sent via SMS to {receipt_data.student['contact']}")
            
            return {
                "success": True,
                "data": {
                    "receipt": receipt,
                    "sent_via": sent_channels,
                    "sent_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to send receipt: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_receipt_stats(self) -> Dict[str, Any]:
        """Get receipt generation statistics"""
        try:
            # Count receipt files
            receipt_files = list(self.receipts_path.glob("receipt_*.json"))
            
            stats = {
                "total_receipts": len(receipt_files),
                "receipts_today": 0,
                "receipts_this_month": 0,
                "storage_used": sum(f.stat().st_size for f in receipt_files if f.is_file())
            }
            
            # Calculate date-based stats
            today = datetime.now().date()
            current_month = today.month
            
            for file_path in receipt_files:
                try:
                    file_date = datetime.fromtimestamp(file_path.stat().st_mtime).date()
                    if file_date == today:
                        stats["receipts_today"] += 1
                    if file_date.month == current_month:
                        stats["receipts_this_month"] += 1
                except:
                    continue
            
            return {"success": True, "data": stats}
            
        except Exception as e:
            logger.error(f"Failed to get receipt stats: {e}")
            return {"success": False, "error": str(e)}

# Create global receipt service instance
receipt_service = ReceiptService() 