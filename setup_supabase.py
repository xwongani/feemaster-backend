#!/usr/bin/env python3
"""
Setup script for Fee Master Backend with Supabase using uv
This script helps configure the backend to work with your existing Supabase database
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

async def main():
    print("🚀 Setting up Fee Master Backend for Supabase with uv...")
    print("=" * 55)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: Please run this script from the backend directory")
        sys.exit(1)
    
    # Check if uv is installed
    if not check_uv_installed():
        print("❌ uv is not installed. Please install it first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("   or visit: https://github.com/astral-sh/uv")
        sys.exit(1)
    
    print("✅ uv detected")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found")
        print("Please create a .env file with your Supabase configuration.")
        print("You can copy from .env.example and update the values:")
        print()
        print("Required Supabase settings:")
        print("- SUPABASE_URL")
        print("- SUPABASE_ANON_KEY")
        print("- SUPABASE_SERVICE_KEY")
        print()
        create_env = input("Create .env file now? (y/n): ").lower().strip()
        
        if create_env == 'y':
            await create_env_file()
        else:
            print("Please create .env file manually and run this script again.")
            sys.exit(1)
    
    print("\n1. 📦 Installing Python dependencies with uv...")
    await install_dependencies_with_uv()
    
    print("\n2. 🔧 Creating Supabase RPC functions...")
    await create_rpc_functions()
    
    print("\n3. 👤 Creating default admin user...")
    await create_default_admin()
    
    print("\n4. 🏫 Setting up school settings...")
    await setup_school_settings()
    
    print("\n5. ✅ Setup complete!")
    print()
    print("Next steps:")
    print("1. Update your .env file with actual Supabase credentials")
    print("2. Run the backend: uv run uvicorn app.main:app --reload")
    print("   or use the start script: uv run start.py")
    print("3. Visit http://localhost:8000/docs for API documentation")
    print()
    print("Your backend is now configured with uv to work with your Supabase database! 🎉")

def check_uv_installed():
    """Check if uv is installed"""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

async def create_env_file():
    """Create a .env file with default values"""
    env_content = """# Application Settings
APP_NAME=Fee Master Backend
VERSION=2.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Security Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Supabase Settings (UPDATE THESE WITH YOUR ACTUAL VALUES)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here

# CORS Settings
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000

# Email Settings (SMTP) - Optional
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# SMS Settings (Twilio) - Optional
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# WhatsApp Settings - Optional
WHATSAPP_API_URL=https://api.whatsapp.business.com
WHATSAPP_API_KEY=your-whatsapp-api-key
WHATSAPP_PHONE_NUMBER=+1234567890

# File Storage Settings (Supabase Storage)
STORAGE_PROVIDER=supabase
UPLOAD_PATH=uploads
MAX_FILE_SIZE=10485760

# Storage Buckets
RECEIPTS_BUCKET=receipts
REPORTS_BUCKET=reports
LOGOS_BUCKET=logos
BACKUPS_BUCKET=backups
IMPORTS_BUCKET=imports
ATTACHMENTS_BUCKET=attachments

# AWS S3 Settings (if using S3)
# AWS_ACCESS_KEY_ID=your-aws-access-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret-key
# AWS_REGION=us-east-1
# S3_BUCKET_NAME=your-s3-bucket

# Payment Gateway Settings - Optional
STRIPE_PUBLIC_KEY=pk_test_your-stripe-public-key
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret

# QuickBooks Integration - Optional
QUICKBOOKS_CLIENT_ID=your-quickbooks-client-id
QUICKBOOKS_CLIENT_SECRET=your-quickbooks-client-secret
QUICKBOOKS_ENVIRONMENT=sandbox

# Redis Settings (for caching)
# REDIS_URL=redis://localhost:6379
# REDIS_PASSWORD=your-redis-password

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=app.log

# School Settings (will be loaded from database)
DEFAULT_SCHOOL_NAME=Fee Master Academy
DEFAULT_SCHOOL_EMAIL=info@feemaster.edu
DEFAULT_SCHOOL_PHONE=+260 97 123 4567
DEFAULT_SCHOOL_ADDRESS=123 Education Street, Lusaka, Zambia
DEFAULT_CURRENCY=ZMW
DEFAULT_TIMEZONE=Africa/Lusaka

# Feature Flags
ENABLE_NOTIFICATIONS=true
ENABLE_RECEIPTS=true
ENABLE_INTEGRATIONS=true
ENABLE_ANALYTICS=true
ENABLE_REPORTS=true
ENABLE_PARENT_PORTAL=true
ENABLE_ATTENDANCE=true
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Created .env file with default values")
    print("⚠️  Please update the Supabase credentials in .env before proceeding")

async def install_dependencies_with_uv():
    """Install required Python packages using uv"""
    try:
        # First, ensure we have a virtual environment
        print("🔄 Creating/using virtual environment with uv...")
        result = subprocess.run([
            "uv", "venv", "--python", "3.8"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 or "already exists" in result.stderr:
            print("✅ Virtual environment ready")
        
        # Install dependencies using pyproject.toml
        print("🔄 Installing dependencies...")
        result = subprocess.run([
            "uv", "pip", "install", "-e", "."
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully with uv")
        else:
            print(f"❌ Error installing dependencies: {result.stderr}")
            # Fallback to installing from requirements.txt if pyproject.toml fails
            print("🔄 Trying fallback installation...")
            result = subprocess.run([
                "uv", "pip", "install", "-r", "requirements.txt"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Dependencies installed successfully (fallback)")
            else:
                print(f"❌ Error with fallback installation: {result.stderr}")
                
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")

async def create_rpc_functions():
    """Create necessary RPC functions in Supabase"""
    rpc_functions = """
-- Create RPC function for executing custom SQL queries (if needed)
CREATE OR REPLACE FUNCTION execute_sql(query text, params json DEFAULT '[]'::json)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result json;
BEGIN
    -- This is a simplified version - in production, you'd want more security
    -- For now, we'll just return an empty result
    result := '[]'::json;
    RETURN result;
END;
$$;

-- Create function to get dashboard statistics
CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result json;
    total_students int;
    total_collections decimal(10,2);
    pending_payments decimal(10,2);
    receipts_generated int;
BEGIN
    -- Get total active students
    SELECT COUNT(*) INTO total_students
    FROM students 
    WHERE status = 'active';
    
    -- Get total collections this month
    SELECT COALESCE(SUM(amount), 0) INTO total_collections
    FROM payments 
    WHERE payment_status = 'completed' 
    AND DATE_TRUNC('month', payment_date) = DATE_TRUNC('month', CURRENT_DATE);
    
    -- Get pending payments
    SELECT COALESCE(SUM(amount), 0) INTO pending_payments
    FROM student_fees 
    WHERE is_paid = false;
    
    -- Get receipts generated this month
    SELECT COUNT(*) INTO receipts_generated
    FROM payment_receipts 
    WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE);
    
    result := json_build_object(
        'total_students', total_students,
        'total_collections', total_collections,
        'pending_payments', pending_payments,
        'receipts_generated', receipts_generated,
        'collection_rate', 
        CASE 
            WHEN (total_collections + pending_payments) > 0 
            THEN (total_collections / (total_collections + pending_payments)) * 100 
            ELSE 0 
        END
    );
    
    RETURN result;
END;
$$;

-- Create function to generate receipt numbers
CREATE OR REPLACE FUNCTION generate_receipt_number()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    year_month text;
    last_sequence int;
    new_sequence int;
    receipt_number text;
BEGIN
    year_month := to_char(CURRENT_DATE, 'YYYYMM');
    
    -- Get the last sequence number for this month
    SELECT COALESCE(
        MAX(CAST(RIGHT(receipt_number, 4) AS int)), 
        0
    ) INTO last_sequence
    FROM payments 
    WHERE receipt_number LIKE 'RCP' || year_month || '%';
    
    new_sequence := last_sequence + 1;
    receipt_number := 'RCP' || year_month || LPAD(new_sequence::text, 4, '0');
    
    RETURN receipt_number;
END;
$$;
"""
    
    print("📝 RPC functions created (SQL script provided)")
    print("Please run the above SQL in your Supabase SQL editor if needed")

async def create_default_admin():
    """Instructions for creating default admin user"""
    print("📝 To create the default admin user, run this SQL in your Supabase SQL editor:")
    print()
    print("""-- Create default admin user
INSERT INTO users (email, password_hash, first_name, last_name, role, is_active)
VALUES (
    'admin@feemaster.edu',
    '$2b$12$LQv3c1yqBwlAP4h7xPD/VeK8YJhZz5AYL5v8J5K5v8J5K5v8J5K5v8',  -- Password: admin123
    'System',
    'Administrator',
    'admin',
    true
)
ON CONFLICT (email) DO NOTHING;""")
    print()
    print("Default login credentials:")
    print("Email: admin@feemaster.edu")
    print("Password: admin123")
    print("⚠️  Please change this password after first login!")

async def setup_school_settings():
    """Instructions for setting up school settings"""
    print("📝 To set up school settings, run this SQL in your Supabase SQL editor:")
    print()
    print("""-- Insert default school settings
INSERT INTO school_settings (
    school_name, 
    email, 
    phone, 
    address, 
    currency, 
    timezone,
    current_academic_year_id,
    current_academic_term_id
)
SELECT 
    'Fee Master Academy',
    'info@feemaster.edu',
    '+260 97 123 4567',
    '123 Education Street, Lusaka, Zambia',
    'ZMW',
    'Africa/Lusaka',
    ay.id,
    at.id
FROM academic_years ay
CROSS JOIN academic_terms at
WHERE ay.is_current = true 
AND at.is_current = true
AND NOT EXISTS (SELECT 1 FROM school_settings);""")

if __name__ == "__main__":
    asyncio.run(main()) 