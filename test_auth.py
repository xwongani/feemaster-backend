#!/usr/bin/env python3
"""
Test script to verify admin user authentication
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import db
from app.routes.auth import verify_password, create_access_token
from datetime import timedelta

async def test_admin_user():
    """Test if admin user exists and can be authenticated"""
    try:
        # Connect to database
        await db.connect()
        
        # Check if admin user exists
        result = await db.execute_query(
            "users",
            "select",
            filters={"email": "admin@feemaster.edu"},
            select_fields="*"
        )
        
        if not result["success"]:
            print("❌ Database query failed:", result.get("error", "Unknown error"))
            return False
            
        if not result["data"]:
            print("❌ Admin user not found in database")
            print("Please run the create_admin_user.sql script in DBeaver")
            return False
            
        user = result["data"][0]
        print(f"✅ Admin user found: {user['email']}")
        print(f"   Role: {user.get('role', 'N/A')}")
        print(f"   Active: {user.get('is_active', 'N/A')}")
        print(f"   Verified: {user.get('is_verified', 'N/A')}")
        
        # Test password verification
        test_password = "admin123"
        if verify_password(test_password, user.get("password_hash", "")):
            print("✅ Password verification successful")
            
            # Test token creation
            from app.config import settings
            access_token = create_access_token(
                data={"sub": user["id"], "email": user["email"], "role": user.get("role", "admin")},
                expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
            )
            print("✅ Token creation successful")
            print(f"   Token: {access_token[:50]}...")
            
            return True
        else:
            print("❌ Password verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing admin user: {e}")
        return False
    finally:
        await db.disconnect()

if __name__ == "__main__":
    print("Testing admin user authentication...")
    success = asyncio.run(test_admin_user())
    
    if success:
        print("\n🎉 Admin user authentication test passed!")
        print("You should be able to login with:")
        print("   Email: admin@feemaster.edu")
        print("   Password: admin123")
    else:
        print("\n❌ Admin user authentication test failed!")
        print("Please check your database setup.") 