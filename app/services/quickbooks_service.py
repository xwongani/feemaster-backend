import logging
from typing import Dict, Optional, List
from datetime import datetime
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from quickbooks.client import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.payment import Payment
from quickbooks.objects.account import Account

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

# Create singleton instance
quickbooks_service = QuickBooksService() 