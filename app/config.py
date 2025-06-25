import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    app_name: str = "Fee Master Backend"
    version: str = "2.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security Settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Supabase Settings (primary database)
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # React App Supabase Settings (for frontend)
    react_app_supabase_url: Optional[str] = None
    react_app_supabase_anon_key: Optional[str] = None
    
    # PostgreSQL Settings (alternative)
    database_url: str = os.getenv("DATABASE_URL", "")
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # CORS Settings
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,https://feemaster.onrender.com,https://feemaster-admin-frontend.onrender.com")
    
    # Email Settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None  # SendGrid API key
    smtp_use_tls: bool = True
    sendgrid_api_key: Optional[str] = None  # Alternative to smtp_password
    
    # SMS Settings
    sms_provider: str = "twilio"  # twilio, africastalking, nexmo
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # WhatsApp Settings
    whatsapp_api_url: Optional[str] = None
    whatsapp_api_key: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    
    # File Storage Settings (Supabase Storage)
    storage_provider: str = "supabase"  # local, s3, supabase
    upload_path: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Storage Buckets
    receipts_bucket: str = "receipts"
    reports_bucket: str = "reports"
    logos_bucket: str = "logos"
    backups_bucket: str = "backups"
    imports_bucket: str = "imports"
    attachments_bucket: str = "attachments"
    
    # AWS S3 Settings (if using S3)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    
    # Payment Gateway Settings
    stripe_public_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    
    # QuickBooks Integration
    quickbooks_client_id: Optional[str] = None
    quickbooks_client_secret: Optional[str] = None
    quickbooks_environment: str = "sandbox"  # sandbox, production
    
    # Redis Settings (for caching)
    redis_url: Optional[str] = None
    redis_password: Optional[str] = None
    
    # Logging Settings
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # Sentry Settings
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN", None)
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # School Settings (will be loaded from database)
    default_school_name: str = "Fee Master Academy"
    default_school_email: str = "info@feemaster.edu"
    default_school_phone: str = "+260 97 123 4567"
    default_school_address: str = "123 Education Street, Lusaka, Zambia"
    default_currency: str = "ZMW"
    default_timezone: str = "Africa/Lusaka"
    
    # Feature Flags
    enable_notifications: bool = True
    enable_receipts: bool = True
    enable_integrations: bool = True
    enable_analytics: bool = True
    enable_reports: bool = True
    enable_parent_portal: bool = True
    enable_attendance: bool = True
    
    # New external integrations and advanced features
    upload_folder: str = "uploads"
    allowed_extensions: list = [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"]
    analytics_enabled: bool = True
    analytics_cache_ttl: int = 3600  # 1 hour
    websocket_enabled: bool = True
    websocket_cleanup_interval: int = 3600  # 1 hour
    audit_trail_enabled: bool = True
    audit_retention_days: int = 365
    bulk_operation_max_records: int = 1000
    bulk_operation_timeout: int = 300  # 5 minutes
    report_generation_enabled: bool = True
    report_storage_path: str = "reports"
    report_retention_days: int = 90
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert cors_origins string to list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # This will ignore extra fields instead of raising errors

# Create settings instance
settings = Settings() 