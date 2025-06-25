#!/usr/bin/env python3
"""
Test script to verify CORS configuration and database connection
"""

import asyncio
import sys
import os
import requests

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import db

def test_cors_config():
    """Test CORS configuration"""
    print("=== CORS Configuration Test ===")
    print(f"CORS Origins String: {settings.cors_origins}")
    print(f"CORS Origins List: {settings.cors_origins_list}")
    print(f"Frontend URL in CORS: {'https://feemaster.onrender.com' in settings.cors_origins_list}")
    print()

async def test_database_connection():
    """Test database connection"""
    print("=== Database Connection Test ===")
    try:
        await db.connect()
        print("✅ Database connection successful")
        
        # Test a simple query
        result = await db.execute_query(
            "users",
            "select",
            filters={"email": "admin@feemaster.edu"},
            select_fields="email, role"
        )
        
        if result["success"]:
            print("✅ Database query successful")
            if result["data"]:
                print(f"✅ Admin user found: {result['data']}")
            else:
                print("⚠️  Admin user not found - you need to run the SQL scripts")
        else:
            print(f"❌ Database query failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    finally:
        await db.disconnect()
    print()

def test_backend_endpoint():
    """Test backend endpoint"""
    print("=== Backend Endpoint Test ===")
    try:
        response = requests.get("https://feemaster-backend-yww7.onrender.com/health")
        print(f"✅ Backend health check: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
    print()

async def main():
    """Run all tests"""
    print("FeeMaster Backend Test Suite")
    print("=" * 50)
    
    test_cors_config()
    await test_database_connection()
    test_backend_endpoint()
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 