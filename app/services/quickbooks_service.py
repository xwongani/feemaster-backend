import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import json
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import asyncio

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class QuickBooksService:
    def __init__(self):
        self.auth_client = None
        self.client = None
        self.initialized = False
        self.realm_id = None
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.cache_dir = "quickbooks_cache"
        self.encryption_key = None
        
        # Ensure cache directory exists
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    async def initialize(self):
        """Initialize QuickBooks client"""
        try:
            from intuitlib.client import AuthClient
            from intuitlib.enums import Scopes
            from quickbooks.objects.base import QuickbooksManager
            
            if not settings.quickbooks_client_id or not settings.quickbooks_client_secret:
                logger.warning("QuickBooks credentials not configured")
                return
            
            # Initialize encryption key for token storage
            self._initialize_encryption()
            
            # Initialize auth client
            self.auth_client = AuthClient(
                client_id=settings.quickbooks_client_id,
                client_secret=settings.quickbooks_client_secret,
                environment=settings.quickbooks_environment,
                redirect_uri=f"{settings.supabase_url}/api/v1/integrations/quickbooks/callback"
            )
            
            # Load existing tokens
            await self._load_tokens()
            
            # Initialize QuickBooks client if tokens exist
            if self.access_token and self.realm_id:
                await self._initialize_client()
            
            self.initialized = True
            logger.info("QuickBooks service initialized successfully")
            
        except ImportError as e:
            logger.error(f"QuickBooks dependencies not installed: {e}")
            logger.info("Install with: pip install intuitlib quickbooks-python")
        except Exception as e:
            logger.error(f"Failed to initialize QuickBooks service: {e}")
    
    def _initialize_encryption(self):
        """Initialize encryption for secure token storage"""
        try:
            # Generate or load encryption key
            key_file = os.path.join(self.cache_dir, "encryption.key")
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    self.encryption_key = f.read()
            else:
                # Generate new key
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(b"feemaster-quickbooks"))
                self.encryption_key = key
                
                # Save key
                with open(key_file, "wb") as f:
                    f.write(key)
                
                # Save salt
                with open(os.path.join(self.cache_dir, "salt.key"), "wb") as f:
                    f.write(salt)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.encryption_key:
            return data
        f = Fernet(self.encryption_key)
        return f.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.encryption_key:
            return encrypted_data
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_data.encode()).decode()
    
    async def _save_tokens(self):
        """Save tokens securely"""
        try:
            token_data = {
                "access_token": self._encrypt_data(self.access_token),
                "refresh_token": self._encrypt_data(self.refresh_token),
                "realm_id": self.realm_id,
                "expires_at": self.token_expiry.isoformat() if self.token_expiry else None
            }
            
            with open(os.path.join(self.cache_dir, "tokens.json"), "w") as f:
                json.dump(token_data, f)
                
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    async def _load_tokens(self):
        """Load tokens from secure storage"""
        try:
            token_file = os.path.join(self.cache_dir, "tokens.json")
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                
                self.access_token = self._decrypt_data(token_data["access_token"])
                self.refresh_token = self._decrypt_data(token_data["refresh_token"])
                self.realm_id = token_data["realm_id"]
                self.token_expiry = datetime.fromisoformat(token_data["expires_at"]) if token_data["expires_at"] else None
                
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
    
    async def _initialize_client(self):
        """Initialize QuickBooks client with tokens"""
        try:
            from quickbooks.objects.base import QuickbooksManager
            
            # Set up QuickBooks manager
            QuickbooksManager.sandbox = settings.quickbooks_environment == "sandbox"
            QuickbooksManager.enable_global()
            
            # Store tokens in QuickBooks manager
            QuickbooksManager.access_token = self.access_token
            QuickbooksManager.refresh_token = self.refresh_token
            QuickbooksManager.realm_id = self.realm_id
            
            self.client = QuickbooksManager
            
        except Exception as e:
            logger.error(f"Failed to initialize QuickBooks client: {e}")
    
    async def get_auth_url(self) -> str:
        """Get QuickBooks authorization URL"""
        try:
            if not self.auth_client:
                raise Exception("QuickBooks auth client not initialized")
            
            scopes = [
                Scopes.ACCOUNTING,
                Scopes.OPENID,
                Scopes.EMAIL,
                Scopes.PROFILE
            ]
            
            auth_url = self.auth_client.get_authorization_url(scopes)
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to get auth URL: {e}")
            raise
    
    async def handle_callback(self, code: str, realm_id: str) -> bool:
        """Handle QuickBooks OAuth callback"""
        try:
            if not self.auth_client:
                raise Exception("QuickBooks auth client not initialized")
            
            # Exchange code for tokens
            self.auth_client.get_bearer_token(code, realm_id=realm_id)
            
            # Store tokens
            self.access_token = self.auth_client.access_token
            self.refresh_token = self.auth_client.refresh_token
            self.realm_id = realm_id
            self.token_expiry = datetime.utcnow() + timedelta(hours=1)
            
            # Save tokens
            await self._save_tokens()
            
            # Initialize client
            await self._initialize_client()
            
            # Log connection
            await self._log_integration_activity("connected", "QuickBooks connected successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle callback: {e}")
            await self._log_integration_activity("error", f"Connection failed: {str(e)}")
            return False
    
    async def refresh_tokens(self) -> bool:
        """Refresh QuickBooks access token"""
        try:
            if not self.auth_client or not self.refresh_token:
                return False
            
            # Refresh tokens
            self.auth_client.refresh(refresh_token=self.refresh_token)
            
            # Update stored tokens
            self.access_token = self.auth_client.access_token
            self.refresh_token = self.auth_client.refresh_token
            self.token_expiry = datetime.utcnow() + timedelta(hours=1)
            
            # Save tokens
            await self._save_tokens()
            
            # Reinitialize client
            await self._initialize_client()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {e}")
            return False
    
    async def create_customer(self, student_data: Dict) -> Optional[str]:
        """Create QuickBooks customer from student data"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return None
            
            from quickbooks.objects.customer import Customer
            
            # Check if customer already exists
            existing_customers = Customer.filter(
                DisplayName=f"{student_data['first_name']} {student_data['last_name']} - {student_data['student_id']}"
            )
            
            if existing_customers:
                return existing_customers[0].Id
            
            # Create new customer
            customer = Customer()
            customer.DisplayName = f"{student_data['first_name']} {student_data['last_name']} - {student_data['student_id']}"
            customer.GivenName = student_data['first_name']
            customer.FamilyName = student_data['last_name']
            customer.CompanyName = f"Student: {student_data['student_id']}"
            
            # Add parent information if available
            if student_data.get('parent_email'):
                customer.PrimaryEmailAddr = customer.PrimaryEmailAddr()
                customer.PrimaryEmailAddr.Address = student_data['parent_email']
            
            if student_data.get('parent_phone'):
                customer.PrimaryPhone = customer.PrimaryPhone()
                customer.PrimaryPhone.FreeFormNumber = student_data['parent_phone']
            
            customer.save()
            
            # Log sync
            await self._log_sync_activity("customer", student_data.get('id'), customer.Id)
            
            return customer.Id
            
        except Exception as e:
            logger.error(f"Failed to create QuickBooks customer: {e}")
            return None
    
    async def create_invoice(self, payment_data: Dict, customer_id: str) -> Optional[str]:
        """Create QuickBooks invoice for payment"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return None
            
            from quickbooks.objects.invoice import Invoice
            from quickbooks.objects.invoiceline import InvoiceLine
            from quickbooks.objects.item import Item
            
            # Create invoice
            invoice = Invoice()
            invoice.CustomerRef = invoice.CustomerRef()
            invoice.CustomerRef.value = customer_id
            
            # Add line items for each fee
            for fee in payment_data.get('fees', []):
                line = InvoiceLine()
                line.Amount = fee['amount']
                line.Description = f"{fee['fee_type']} - {fee['description']}"
                
                # Get or create item
                item_name = f"School Fee - {fee['fee_type']}"
                items = Item.filter(Name=item_name)
                if items:
                    line.ItemBasedExpenseLineDetail = line.ItemBasedExpenseLineDetail()
                    line.ItemBasedExpenseLineDetail.ItemRef = line.ItemBasedExpenseLineDetail.ItemRef()
                    line.ItemBasedExpenseLineDetail.ItemRef.value = items[0].Id
                else:
                    # Create item if it doesn't exist
                    item = Item()
                    item.Name = item_name
                    item.Type = "Service"
                    item.save()
                    
                    line.ItemBasedExpenseLineDetail = line.ItemBasedExpenseLineDetail()
                    line.ItemBasedExpenseLineDetail.ItemRef = line.ItemBasedExpenseLineDetail.ItemRef()
                    line.ItemBasedExpenseLineDetail.ItemRef.value = item.Id
                
                invoice.Line.append(line)
            
            invoice.save()
            
            # Log sync
            await self._log_sync_activity("invoice", payment_data.get('id'), invoice.Id)
            
            return invoice.Id
            
        except Exception as e:
            logger.error(f"Failed to create QuickBooks invoice: {e}")
            return None
    
    async def create_payment(self, payment_data: Dict, invoice_id: str) -> Optional[str]:
        """Create QuickBooks payment for invoice"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return None
            
            from quickbooks.objects.payment import Payment
            from quickbooks.objects.linkedtxn import LinkedTxn
            
            # Create payment
            payment = Payment()
            payment.TotalAmt = payment_data['amount']
            payment.CustomerRef = payment.CustomerRef()
            payment.CustomerRef.value = payment_data['customer_id']
            
            # Link to invoice
            linked_txn = LinkedTxn()
            linked_txn.TxnId = invoice_id
            linked_txn.TxnType = "Invoice"
            payment.LinkedTxn.append(linked_txn)
            
            # Set payment method
            payment_method_map = {
                'cash': 'Cash',
                'credit-card': 'Credit Card',
                'mobile-money': 'Mobile Money',
                'bank-transfer': 'Bank Transfer'
            }
            
            payment.PaymentMethodRef = payment.PaymentMethodRef()
            payment.PaymentMethodRef.name = payment_method_map.get(
                payment_data['payment_method'], 'Cash'
            )
            
            payment.save()
            
            # Log sync
            await self._log_sync_activity("payment", payment_data.get('id'), payment.Id)
            
            return payment.Id
            
        except Exception as e:
            logger.error(f"Failed to create QuickBooks payment: {e}")
            return None
    
    async def sync_payment(self, payment_data: Dict) -> Dict:
        """Sync payment to QuickBooks"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return {"success": False, "error": "QuickBooks not connected"}
            
            # Get student data
            student_result = await db.execute_query(
                "students",
                "select",
                filters={"id": payment_data['student_id']},
                select_fields="*"
            )
            
            if not student_result["success"] or not student_result["data"]:
                return {"success": False, "error": "Student not found"}
            
            student = student_result["data"][0]
            
            # Create or get customer
            customer_id = await self.create_customer(student)
            if not customer_id:
                return {"success": False, "error": "Failed to create customer"}
            
            # Create invoice
            invoice_id = await self.create_invoice(payment_data, customer_id)
            if not invoice_id:
                return {"success": False, "error": "Failed to create invoice"}
            
            # Create payment
            payment_id = await self.create_payment(payment_data, invoice_id)
            if not payment_id:
                return {"success": False, "error": "Failed to create payment"}
            
            return {
                "success": True,
                "customer_id": customer_id,
                "invoice_id": invoice_id,
                "payment_id": payment_id
            }
            
        except Exception as e:
            logger.error(f"Failed to sync payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_accounts(self) -> List[Dict]:
        """Get QuickBooks accounts"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return []
            
            from quickbooks.objects.account import Account
            
            accounts = Account.all()
            return [
                {
                    "id": account.Id,
                    "name": account.Name,
                    "type": account.AccountType,
                    "sub_type": account.AccountSubType,
                    "balance": account.CurrentBalance
                }
                for account in accounts
            ]
            
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            return []
    
    async def get_payment_methods(self) -> List[Dict]:
        """Get QuickBooks payment methods"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return []
            
            from quickbooks.objects.paymentmethod import PaymentMethod
            
            methods = PaymentMethod.all()
            return [
                {
                    "id": method.Id,
                    "name": method.Name,
                    "type": method.Type
                }
                for method in methods
            ]
            
        except Exception as e:
            logger.error(f"Failed to get payment methods: {e}")
            return [
                {"id": "1", "name": "Cash", "type": "NON_CREDIT_CARD"},
                {"id": "2", "name": "Credit Card", "type": "CREDIT_CARD"},
                {"id": "3", "name": "Bank Transfer", "type": "NON_CREDIT_CARD"},
                {"id": "4", "name": "Check", "type": "NON_CREDIT_CARD"}
            ]
    
    async def _ensure_valid_tokens(self):
        """Ensure tokens are valid and refresh if needed"""
        try:
            if not self.access_token or (self.token_expiry and datetime.utcnow() >= self.token_expiry):
                await self.refresh_tokens()
        except Exception as e:
            logger.error(f"Failed to ensure valid tokens: {e}")
    
    async def _log_integration_activity(self, action: str, message: str):
        """Log integration activity"""
        try:
            await db.execute_query(
                "integration_logs",
                "insert",
                data={
                    "integration_name": "quickbooks",
                    "action": action,
                    "status": "success" if action == "connected" else "error",
                    "request_data": {},
                    "response_data": {"message": message},
                    "error_message": None if action == "connected" else message
                }
            )
        except Exception as e:
            logger.error(f"Failed to log integration activity: {e}")
    
    async def _log_sync_activity(self, entity_type: str, entity_id: str, quickbooks_id: str):
        """Log sync activity"""
        try:
            await db.execute_query(
                "quickbooks_sync_logs",
                "insert",
                data={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "quickbooks_id": quickbooks_id,
                    "sync_status": "success",
                    "error_message": None
                }
            )
        except Exception as e:
            logger.error(f"Failed to log sync activity: {e}")
    
    async def sync_payments_to_cache(self, days_back: int = 30) -> Dict:
        """Sync payment data from QuickBooks to encrypted local cache"""
        try:
            if not self.client:
                await self._ensure_valid_tokens()
                if not self.client:
                    return {"success": False, "error": "QuickBooks not connected"}
            
            from quickbooks.objects.payment import Payment
            from datetime import datetime, timedelta
            
            # Get payments from QuickBooks
            start_date = datetime.utcnow() - timedelta(days=days_back)
            payments = Payment.filter(
                TxnDate__gte=start_date.strftime("%Y-%m-%d")
            )
            
            # Cache payments
            cache_data = []
            for payment in payments:
                cache_data.append({
                    "id": payment.Id,
                    "amount": payment.TotalAmt,
                    "date": payment.TxnDate,
                    "customer_id": payment.CustomerRef.value if payment.CustomerRef else None,
                    "payment_method": payment.PaymentMethodRef.name if payment.PaymentMethodRef else None
                })
            
            # Save to encrypted cache
            cache_file = os.path.join(self.cache_dir, "payments_cache.json")
            encrypted_data = self._encrypt_data(json.dumps(cache_data))
            
            with open(cache_file, "w") as f:
                json.dump({"data": encrypted_data, "timestamp": datetime.utcnow().isoformat()}, f)
            
            return {
                "success": True,
                "records_synced": len(cache_data),
                "cache_file": cache_file
            }
            
        except Exception as e:
            logger.error(f"Failed to sync payments to cache: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_payment_analytics(self) -> Dict:
        """Get payment analytics from local cache"""
        try:
            cache_file = os.path.join(self.cache_dir, "payments_cache.json")
            if not os.path.exists(cache_file):
                return {"success": False, "error": "No cached data available"}
            
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
            
            # Decrypt and parse data
            encrypted_data = cache_data["data"]
            payments = json.loads(self._decrypt_data(encrypted_data))
            
            # Calculate analytics
            total_amount = sum(payment["amount"] for payment in payments)
            payment_count = len(payments)
            
            # Group by payment method
            method_totals = {}
            for payment in payments:
                method = payment.get("payment_method", "Unknown")
                method_totals[method] = method_totals.get(method, 0) + payment["amount"]
            
            # Group by date
            date_totals = {}
            for payment in payments:
                date = payment["date"]
                date_totals[date] = date_totals.get(date, 0) + payment["amount"]
            
            return {
                "success": True,
                "total_amount": total_amount,
                "payment_count": payment_count,
                "method_breakdown": method_totals,
                "date_breakdown": date_totals,
                "last_sync": cache_data["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment analytics: {e}")
            return {"success": False, "error": str(e)}

# Initialize service
quickbooks_service = QuickBooksService() 