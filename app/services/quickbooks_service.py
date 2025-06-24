import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from quickbooks.client import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.payment import Payment
from quickbooks.objects.account import Account
import json
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

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
            if settings.enable_integrations:
                self.auth_client = AuthClient(
                    client_id=settings.quickbooks_client_id,
                    client_secret=settings.quickbooks_client_secret,
                    environment=settings.quickbooks_environment,
                    redirect_uri=settings.quickbooks_redirect_uri
                )
                
                # Initialize encryption key
                await self._initialize_encryption()
                
                # Load saved tokens from database
                tokens = await self._load_tokens()
                if tokens:
                    self.realm_id = tokens.get("realm_id")
                    self.access_token = tokens.get("access_token")
                    self.refresh_token = tokens.get("refresh_token")
                    self.token_expiry = datetime.fromisoformat(tokens.get("token_expiry"))
                    
                    # Initialize client if we have tokens
                    if self.access_token and self.realm_id:
                        self.client = QuickBooks(
                            client_id=settings.quickbooks_client_id,
                            client_secret=settings.quickbooks_client_secret,
                            access_token=self.access_token,
                            company_id=self.realm_id,
                            environment=settings.quickbooks_environment
                        )
                        self.initialized = True
                        logger.info("QuickBooks client initialized with saved tokens")
                
                logger.info("QuickBooks service initialized")
            else:
                logger.info("QuickBooks integration disabled in settings")
                
        except Exception as e:
            logger.error(f"Failed to initialize QuickBooks service: {e}")
    
    async def _initialize_encryption(self):
        """Initialize encryption key for local cache"""
        try:
            # Use a combination of settings for key derivation
            salt = settings.quickbooks_client_secret.encode()[:16]
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(settings.quickbooks_client_id.encode()))
            self.encryption_key = Fernet(key)
            logger.info("Encryption key initialized for QuickBooks cache")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self.encryption_key = None
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data for local storage"""
        if not self.encryption_key:
            raise Exception("Encryption key not initialized")
        return self.encryption_key.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data from local storage"""
        if not self.encryption_key:
            raise Exception("Encryption key not initialized")
        return self.encryption_key.decrypt(encrypted_data.encode()).decode()
    
    def _get_cache_file_path(self, filename: str) -> str:
        """Get full path for cache file"""
        return os.path.join(self.cache_dir, filename)
    
    async def _save_to_cache(self, filename: str, data: Dict) -> bool:
        """Save encrypted data to local cache"""
        try:
            file_path = self._get_cache_file_path(filename)
            encrypted_data = self._encrypt_data(json.dumps(data))
            
            with open(file_path, 'w') as f:
                f.write(encrypted_data)
            
            logger.info(f"Data saved to cache: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to cache {filename}: {e}")
            return False
    
    async def _load_from_cache(self, filename: str) -> Optional[Dict]:
        """Load and decrypt data from local cache"""
        try:
            file_path = self._get_cache_file_path(filename)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"Failed to load from cache {filename}: {e}")
            return None
    
    async def _delete_cache_file(self, filename: str) -> bool:
        """Delete cache file"""
        try:
            file_path = self._get_cache_file_path(filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cache file deleted: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache file {filename}: {e}")
            return False
    
    async def _load_tokens(self) -> Optional[Dict]:
        """Load QuickBooks tokens from database"""
        try:
            result = await db.execute_query(
                "quickbooks_tokens",
                "select",
                filters={"is_active": True},
                limit=1
            )
            
            if result["success"] and result["data"]:
                return result["data"][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to load QuickBooks tokens: {e}")
            return None
    
    async def _save_tokens(self, tokens: Dict):
        """Save QuickBooks tokens to database"""
        try:
            # Deactivate old tokens
            await db.execute_query(
                "quickbooks_tokens",
                "update",
                filters={"is_active": True},
                data={"is_active": False}
            )
            
            # Save new tokens
            await db.execute_query(
                "quickbooks_tokens",
                "insert",
                data={
                    "realm_id": tokens["realm_id"],
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_expiry": tokens["token_expiry"],
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to save QuickBooks tokens: {e}")
    
    async def get_auth_url(self) -> str:
        """Get QuickBooks authorization URL"""
        try:
            scopes = [
                Scopes.ACCOUNTING,
                Scopes.OPENID,
                Scopes.EMAIL,
                Scopes.PROFILE
            ]
            
            auth_url = self.auth_client.get_authorization_url(scopes)
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to get QuickBooks auth URL: {e}")
            raise
    
    async def handle_callback(self, code: str, realm_id: str) -> bool:
        """Handle QuickBooks OAuth callback"""
        try:
            # Exchange code for tokens
            self.auth_client.get_bearer_token(code)
            
            # Save tokens
            tokens = {
                "realm_id": realm_id,
                "access_token": self.auth_client.access_token,
                "refresh_token": self.auth_client.refresh_token,
                "token_expiry": self.auth_client.expires_in
            }
            
            await self._save_tokens(tokens)
            
            # Initialize client
            self.client = QuickBooks(
                client_id=settings.quickbooks_client_id,
                client_secret=settings.quickbooks_client_secret,
                access_token=self.auth_client.access_token,
                company_id=realm_id,
                environment=settings.quickbooks_environment
            )
            
            self.initialized = True
            logger.info("QuickBooks authorization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle QuickBooks callback: {e}")
            return False
    
    async def refresh_tokens(self) -> bool:
        """Refresh QuickBooks access token"""
        try:
            if not self.refresh_token:
                logger.warning("No refresh token available")
                return False
            
            self.auth_client.refresh(refresh_token=self.refresh_token)
            
            # Save new tokens
            tokens = {
                "realm_id": self.realm_id,
                "access_token": self.auth_client.access_token,
                "refresh_token": self.auth_client.refresh_token,
                "token_expiry": self.auth_client.expires_in
            }
            
            await self._save_tokens(tokens)
            
            # Update client
            self.client = QuickBooks(
                client_id=settings.quickbooks_client_id,
                client_secret=settings.quickbooks_client_secret,
                access_token=self.auth_client.access_token,
                company_id=self.realm_id,
                environment=settings.quickbooks_environment
            )
            
            logger.info("QuickBooks tokens refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh QuickBooks tokens: {e}")
            return False
    
    async def create_customer(self, student_data: Dict) -> Optional[str]:
        """Create QuickBooks customer from student data"""
        try:
            if not self.initialized:
                logger.warning("QuickBooks client not initialized")
                return None
            
            customer = Customer()
            customer.CompanyName = f"{student_data['first_name']} {student_data['last_name']}"
            customer.DisplayName = customer.CompanyName
            customer.GivenName = student_data['first_name']
            customer.FamilyName = student_data['last_name']
            
            if student_data.get('email'):
                customer.PrimaryEmailAddr = student_data['email']
            
            if student_data.get('phone'):
                customer.PrimaryPhone = student_data['phone']
            
            customer.save(qb=self.client)
            logger.info(f"Created QuickBooks customer: {customer.Id}")
            return customer.Id
            
        except Exception as e:
            logger.error(f"Failed to create QuickBooks customer: {e}")
            return None
    
    async def create_invoice(self, payment_data: Dict, customer_id: str) -> Optional[str]:
        """Create QuickBooks invoice for payment"""
        try:
            if not self.initialized:
                logger.warning("QuickBooks client not initialized")
                return None
            
            invoice = Invoice()
            invoice.CustomerRef = customer_id
            
            # Add line items
            line = invoice.Line.add()
            line.Amount = payment_data['amount']
            line.DetailType = "SalesItemLineDetail"
            line.SalesItemLineDetail.ItemRef = payment_data.get('item_id', '1')  # Default item ID
            
            invoice.save(qb=self.client)
            logger.info(f"Created QuickBooks invoice: {invoice.Id}")
            return invoice.Id
            
        except Exception as e:
            logger.error(f"Failed to create QuickBooks invoice: {e}")
            return None
    
    async def create_payment(self, payment_data: Dict, invoice_id: str) -> Optional[str]:
        """Create QuickBooks payment for invoice"""
        try:
            if not self.initialized:
                logger.warning("QuickBooks client not initialized")
                return None
            
            payment = Payment()
            payment.CustomerRef = payment_data['customer_id']
            payment.TotalAmt = payment_data['amount']
            payment.PaymentMethodRef = payment_data.get('payment_method_id', '1')  # Default payment method
            
            # Link to invoice
            payment.Line.add()
            payment.Line[0].Amount = payment_data['amount']
            payment.Line[0].LinkedTxn.add()
            payment.Line[0].LinkedTxn[0].TxnId = invoice_id
            payment.Line[0].LinkedTxn[0].TxnType = "Invoice"
            
            payment.save(qb=self.client)
            logger.info(f"Created QuickBooks payment: {payment.Id}")
            return payment.Id
            
        except Exception as e:
            logger.error(f"Failed to create QuickBooks payment: {e}")
            return None
    
    async def sync_payment(self, payment_data: Dict) -> Dict:
        """Sync payment to QuickBooks"""
        try:
            if not self.initialized:
                logger.warning("QuickBooks client not initialized")
                return {"success": False, "error": "QuickBooks client not initialized"}
            
            # Get or create customer
            customer_id = await self.create_customer(payment_data['student'])
            if not customer_id:
                return {"success": False, "error": "Failed to create customer"}
            
            # Create invoice
            invoice_id = await self.create_invoice(payment_data, customer_id)
            if not invoice_id:
                return {"success": False, "error": "Failed to create invoice"}
            
            # Create payment
            payment_id = await self.create_payment(
                {**payment_data, "customer_id": customer_id},
                invoice_id
            )
            
            if not payment_id:
                return {"success": False, "error": "Failed to create payment"}
            
            return {
                "success": True,
                "data": {
                    "customer_id": customer_id,
                    "invoice_id": invoice_id,
                    "payment_id": payment_id
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to sync payment to QuickBooks: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_accounts(self) -> List[Dict]:
        """Get QuickBooks accounts"""
        try:
            if not self.initialized:
                logger.warning("QuickBooks client not initialized")
                return []
            
            accounts = Account.all(qb=self.client)
            return [
                {
                    "id": account.Id,
                    "name": account.Name,
                    "type": account.AccountType,
                    "sub_type": account.AccountSubType,
                    "active": account.Active
                }
                for account in accounts
            ]
            
        except Exception as e:
            logger.error(f"Failed to get QuickBooks accounts: {e}")
            return []
    
    async def get_payment_methods(self) -> List[Dict]:
        """Get QuickBooks payment methods"""
        try:
            if not self.initialized:
                logger.warning("QuickBooks client not initialized")
                return []
            
            # This is a simplified version. In production, you'd want to cache this
            # and handle pagination properly
            payment_methods = [
                {"id": "1", "name": "Cash"},
                {"id": "2", "name": "Credit Card"},
                {"id": "3", "name": "Bank Transfer"},
                {"id": "4", "name": "Check"}
            ]
            
            return payment_methods
            
        except Exception as e:
            logger.error(f"Failed to get QuickBooks payment methods: {e}")
            return []
    
    async def sync_payments_to_cache(self, days_back: int = 30) -> Dict:
        """Sync payment data from QuickBooks to encrypted local cache"""
        try:
            if not self.initialized:
                return {"success": False, "error": "QuickBooks client not initialized"}
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Fetch payments from QuickBooks
            payments = Payment.filter(
                TxnDate__gte=start_date.strftime("%Y-%m-%d"),
                TxnDate__lte=end_date.strftime("%Y-%m-%d"),
                qb=self.client
            )
            
            payment_data = []
            for payment in payments:
                payment_info = {
                    "id": payment.Id,
                    "customer_ref": payment.CustomerRef.value if payment.CustomerRef else None,
                    "amount": float(payment.TotalAmt),
                    "payment_method": payment.PaymentMethodRef.value if payment.PaymentMethodRef else None,
                    "date": payment.TxnDate,
                    "memo": payment.PrivateNote,
                    "status": "completed"
                }
                payment_data.append(payment_info)
            
            # Save to cache with metadata
            cache_data = {
                "sync_timestamp": datetime.utcnow().isoformat(),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_payments": len(payment_data),
                "payments": payment_data
            }
            
            success = await self._save_to_cache("payments.json", cache_data)
            
            if success:
                # Update sync status in database
                await self._update_sync_status("payments", True, len(payment_data))
                return {
                    "success": True,
                    "data": {
                        "total_payments": len(payment_data),
                        "date_range": cache_data["date_range"],
                        "sync_timestamp": cache_data["sync_timestamp"]
                    }
                }
            else:
                await self._update_sync_status("payments", False, 0, "Failed to save to cache")
                return {"success": False, "error": "Failed to save payment data to cache"}
                
        except Exception as e:
            logger.error(f"Failed to sync payments to cache: {e}")
            await self._update_sync_status("payments", False, 0, str(e))
            return {"success": False, "error": str(e)}
    
    async def get_payment_analytics(self) -> Dict:
        """Get payment analytics from local cache"""
        try:
            cache_data = await self._load_from_cache("payments.json")
            if not cache_data:
                return {"success": False, "error": "No payment data available in cache"}
            
            payments = cache_data.get("payments", [])
            
            # Calculate analytics
            total_amount = sum(p["amount"] for p in payments)
            payment_methods = {}
            daily_totals = {}
            
            for payment in payments:
                # Payment methods breakdown
                method = payment.get("payment_method", "Unknown")
                if method not in payment_methods:
                    payment_methods[method] = {"count": 0, "amount": 0}
                payment_methods[method]["count"] += 1
                payment_methods[method]["amount"] += payment["amount"]
                
                # Daily totals
                date = payment.get("date", "")
                if date not in daily_totals:
                    daily_totals[date] = 0
                daily_totals[date] += payment["amount"]
            
            # Sort daily totals by date
            sorted_daily = sorted(daily_totals.items())
            
            analytics = {
                "summary": {
                    "total_payments": len(payments),
                    "total_amount": total_amount,
                    "average_payment": total_amount / len(payments) if payments else 0,
                    "sync_timestamp": cache_data.get("sync_timestamp"),
                    "date_range": cache_data.get("date_range")
                },
                "payment_methods": [
                    {
                        "method": method,
                        "count": data["count"],
                        "amount": data["amount"],
                        "percentage": (data["amount"] / total_amount * 100) if total_amount > 0 else 0
                    }
                    for method, data in payment_methods.items()
                ],
                "daily_trends": [
                    {"date": date, "amount": amount}
                    for date, amount in sorted_daily
                ]
            }
            
            return {"success": True, "data": analytics}
            
        except Exception as e:
            logger.error(f"Failed to get payment analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_sync_status(self) -> Dict:
        """Get QuickBooks sync status"""
        try:
            # Get last sync status from database
            result = await db.execute_query(
                "quickbooks_sync_logs",
                "select",
                filters={"sync_type": "payments"},
                order_by="created_at DESC",
                limit=1
            )
            
            if result["success"] and result["data"]:
                last_sync = result["data"][0]
                return {
                    "success": True,
                    "data": {
                        "connected": self.initialized,
                        "last_sync": last_sync.get("created_at"),
                        "last_sync_success": last_sync.get("success"),
                        "records_synced": last_sync.get("records_synced", 0),
                        "error_message": last_sync.get("error_message"),
                        "realm_id": self.realm_id
                    }
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "connected": self.initialized,
                        "last_sync": None,
                        "last_sync_success": False,
                        "records_synced": 0,
                        "error_message": "No sync history found",
                        "realm_id": self.realm_id
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {"success": False, "error": str(e)}
    
    async def _update_sync_status(self, sync_type: str, success: bool, records_synced: int, error_message: str = None):
        """Update sync status in database"""
        try:
            await db.execute_query(
                "quickbooks_sync_logs",
                "insert",
                data={
                    "sync_type": sync_type,
                    "success": success,
                    "records_synced": records_synced,
                    "error_message": error_message,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")
    
    async def clear_cache(self) -> Dict:
        """Clear all cached QuickBooks data"""
        try:
            # Delete all cache files
            cache_files = ["payments.json"]
            deleted_count = 0
            
            for filename in cache_files:
                if await self._delete_cache_file(filename):
                    deleted_count += 1
            
            logger.info(f"Cleared {deleted_count} cache files")
            return {
                "success": True,
                "data": {
                    "deleted_files": deleted_count,
                    "message": "Cache cleared successfully"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return {"success": False, "error": str(e)}

# Create singleton instance
quickbooks_service = QuickBooksService() 