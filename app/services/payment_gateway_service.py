import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import stripe
import paypalrestsdk
from decimal import Decimal

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class PaymentGatewayService:
    def __init__(self):
        self.stripe_client = None
        self.paypal_client = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize payment gateway clients"""
        try:
            # Initialize Stripe
            if settings.stripe_secret_key:
                stripe.api_key = settings.stripe_secret_key
                self.stripe_client = stripe
                logger.info("Stripe client initialized")
            
            # Initialize PayPal
            if settings.paypal_client_id and settings.paypal_client_secret:
                paypalrestsdk.configure({
                    "mode": "sandbox" if settings.environment == "development" else "live",
                    "client_id": settings.paypal_client_id,
                    "client_secret": settings.paypal_client_secret
                })
                self.paypal_client = paypalrestsdk
                logger.info("PayPal client initialized")
            
            self.initialized = True
            logger.info("Payment gateway service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize payment gateway service: {e}")
    
    async def create_stripe_payment_intent(self, amount: float, currency: str = "zmw", metadata: Dict = None) -> Dict:
        """Create Stripe payment intent"""
        try:
            if not self.stripe_client:
                return {"success": False, "error": "Stripe not configured"}
            
            # Convert amount to cents (Stripe requirement)
            amount_cents = int(amount * 100)
            
            intent_data = {
                "amount": amount_cents,
                "currency": currency.lower(),
                "automatic_payment_methods": {
                    "enabled": True,
                }
            }
            
            if metadata:
                intent_data["metadata"] = metadata
            
            intent = self.stripe_client.PaymentIntent.create(**intent_data)
            
            return {
                "success": True,
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "amount": amount,
                "currency": currency
            }
            
        except Exception as e:
            logger.error(f"Failed to create Stripe payment intent: {e}")
            return {"success": False, "error": str(e)}
    
    async def confirm_stripe_payment(self, payment_intent_id: str) -> Dict:
        """Confirm Stripe payment"""
        try:
            if not self.stripe_client:
                return {"success": False, "error": "Stripe not configured"}
            
            intent = self.stripe_client.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == "succeeded":
                return {
                    "success": True,
                    "status": "succeeded",
                    "amount": intent.amount / 100,
                    "currency": intent.currency,
                    "transaction_id": intent.id
                }
            elif intent.status == "requires_payment_method":
                return {
                    "success": False,
                    "error": "Payment method required",
                    "status": intent.status
                }
            else:
                return {
                    "success": False,
                    "error": f"Payment status: {intent.status}",
                    "status": intent.status
                }
                
        except Exception as e:
            logger.error(f"Failed to confirm Stripe payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_paypal_payment(self, amount: float, currency: str = "ZMW", description: str = "", return_url: str = "", cancel_url: str = "") -> Dict:
        """Create PayPal payment"""
        try:
            if not self.paypal_client:
                return {"success": False, "error": "PayPal not configured"}
            
            payment = self.paypal_client.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": return_url,
                    "cancel_url": cancel_url
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": "School Fees",
                            "sku": "FEES",
                            "price": str(amount),
                            "currency": currency,
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }]
            })
            
            if payment.create():
                # Get approval URL
                for link in payment.links:
                    if link.rel == "approval_url":
                        return {
                            "success": True,
                            "payment_id": payment.id,
                            "approval_url": link.href,
                            "amount": amount,
                            "currency": currency
                        }
                
                return {"success": False, "error": "Approval URL not found"}
            else:
                return {"success": False, "error": str(payment.error)}
                
        except Exception as e:
            logger.error(f"Failed to create PayPal payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_paypal_payment(self, payment_id: str, payer_id: str) -> Dict:
        """Execute PayPal payment"""
        try:
            if not self.paypal_client:
                return {"success": False, "error": "PayPal not configured"}
            
            payment = self.paypal_client.Payment.find(payment_id)
            
            if payment.execute({"payer_id": payer_id}):
                # Get transaction details
                transaction = payment.transactions[0]
                return {
                    "success": True,
                    "status": "completed",
                    "amount": float(transaction.amount.total),
                    "currency": transaction.amount.currency,
                    "transaction_id": payment.id,
                    "payer_id": payer_id
                }
            else:
                return {"success": False, "error": str(payment.error)}
                
        except Exception as e:
            logger.error(f"Failed to execute PayPal payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_online_payment(self, payment_data: Dict, gateway: str = "stripe") -> Dict:
        """Process online payment through specified gateway"""
        try:
            if gateway.lower() == "stripe":
                return await self._process_stripe_payment(payment_data)
            elif gateway.lower() == "paypal":
                return await self._process_paypal_payment(payment_data)
            else:
                return {"success": False, "error": f"Unsupported gateway: {gateway}"}
                
        except Exception as e:
            logger.error(f"Failed to process online payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_stripe_payment(self, payment_data: Dict) -> Dict:
        """Process payment through Stripe"""
        try:
            # Create payment intent
            intent_result = await self.create_stripe_payment_intent(
                amount=payment_data["amount"],
                currency=payment_data.get("currency", "zmw"),
                metadata={
                    "student_id": payment_data["student_id"],
                    "receipt_number": payment_data.get("receipt_number", ""),
                    "payment_method": "stripe"
                }
            )
            
            if not intent_result["success"]:
                return intent_result
            
            # Store payment intent for later confirmation
            await self._store_payment_intent(intent_result["payment_intent_id"], payment_data)
            
            return {
                "success": True,
                "gateway": "stripe",
                "client_secret": intent_result["client_secret"],
                "payment_intent_id": intent_result["payment_intent_id"],
                "requires_action": True
            }
            
        except Exception as e:
            logger.error(f"Failed to process Stripe payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_paypal_payment(self, payment_data: Dict) -> Dict:
        """Process payment through PayPal"""
        try:
            # Create PayPal payment
            payment_result = await self.create_paypal_payment(
                amount=payment_data["amount"],
                currency=payment_data.get("currency", "ZMW"),
                description=f"School fees payment - {payment_data.get('receipt_number', '')}",
                return_url=f"{settings.supabase_url}/api/v1/payments/paypal/success",
                cancel_url=f"{settings.supabase_url}/api/v1/payments/paypal/cancel"
            )
            
            if not payment_result["success"]:
                return payment_result
            
            # Store payment for later execution
            await self._store_paypal_payment(payment_result["payment_id"], payment_data)
            
            return {
                "success": True,
                "gateway": "paypal",
                "payment_id": payment_result["payment_id"],
                "approval_url": payment_result["approval_url"],
                "requires_action": True
            }
            
        except Exception as e:
            logger.error(f"Failed to process PayPal payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_payment_intent(self, payment_intent_id: str, payment_data: Dict):
        """Store payment intent for later processing"""
        try:
            await db.execute_query(
                "payment_gateway_logs",
                "insert",
                data={
                    "gateway": "stripe",
                    "gateway_payment_id": payment_intent_id,
                    "local_payment_id": payment_data.get("payment_id"),
                    "amount": payment_data["amount"],
                    "currency": payment_data.get("currency", "zmw"),
                    "status": "pending",
                    "metadata": payment_data,
                    "created_at": datetime.utcnow()
                }
            )
        except Exception as e:
            logger.error(f"Failed to store payment intent: {e}")
    
    async def _store_paypal_payment(self, payment_id: str, payment_data: Dict):
        """Store PayPal payment for later processing"""
        try:
            await db.execute_query(
                "payment_gateway_logs",
                "insert",
                data={
                    "gateway": "paypal",
                    "gateway_payment_id": payment_id,
                    "local_payment_id": payment_data.get("payment_id"),
                    "status": "pending",
                    "metadata": payment_data,
                    "created_at": datetime.utcnow()
                }
            )
        except Exception as e:
            logger.error(f"Failed to store PayPal payment: {e}")
    
    async def get_payment_methods(self) -> List[Dict]:
        """Get available payment methods"""
        methods = []
        
        if self.stripe_client:
            methods.append({
                "id": "stripe",
                "name": "Credit/Debit Card",
                "type": "card",
                "gateway": "stripe",
                "enabled": True
            })
        
        if self.paypal_client:
            methods.append({
                "id": "paypal",
                "name": "PayPal",
                "type": "paypal",
                "gateway": "paypal",
                "enabled": True
            })
        
        return methods
    
    async def get_gateway_status(self) -> Dict:
        """Get payment gateway status"""
        return {
            "stripe": {
                "enabled": bool(self.stripe_client),
                "mode": "test" if settings.environment == "development" else "live"
            },
            "paypal": {
                "enabled": bool(self.paypal_client),
                "mode": "sandbox" if settings.environment == "development" else "live"
            }
        }

# Initialize service
payment_gateway_service = PaymentGatewayService()
