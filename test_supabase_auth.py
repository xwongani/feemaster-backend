import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
API_BASE = "http://localhost:8000/api/v1"

def test_supabase_login():
    """Test login using Supabase Auth"""
    print("Testing Supabase authentication...\n")
    
    # Test user credentials - we'll need to create this user in Supabase first
    test_email = "admin@example.com"
    test_password = "admin123"
    
    # Login via Supabase Auth
    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    login_data = {
        "email": test_email,
        "password": test_password
    }
    
    print(f"Attempting login to: {auth_url}")
    response = requests.post(auth_url, headers=headers, json=login_data)
    
    print(f"Login Status: {response.status_code}")
    print(f"Login Response: {response.text[:200]}...")
    
    if response.status_code == 200:
        result = response.json()
        access_token = result.get("access_token")
        
        if access_token:
            print(f"✅ Login successful! Token: {access_token[:50]}...")
            
            # Test our backend API with the Supabase token
            print("\nTesting backend API with Supabase token...")
            
            students_response = requests.get(
                f"{API_BASE}/students",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
            )
            
            print(f"Students API Status: {students_response.status_code}")
            print(f"Students Response: {students_response.text[:300]}...")
            
            return True, access_token
        else:
            print("❌ Login failed: No access token in response")
            return False, None
    else:
        print(f"❌ Login failed with status {response.status_code}")
        if response.status_code == 400:
            print("This usually means the user doesn't exist in Supabase Auth")
            print("You need to create a user in Supabase Auth first")
        return False, None

def create_supabase_user():
    """Create a test user in Supabase Auth"""
    print("Creating test user in Supabase Auth...\n")
    
    signup_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    user_data = {
        "email": "admin@example.com",
        "password": "admin123",
        "data": {
            "first_name": "Admin",
            "last_name": "User",
            "role": "admin"
        }
    }
    
    response = requests.post(signup_url, headers=headers, json=user_data)
    
    print(f"Signup Status: {response.status_code}")
    print(f"Signup Response: {response.text[:300]}...")
    
    if response.status_code == 200:
        print("✅ User created successfully!")
        return True
    else:
        print("❌ Failed to create user")
        return False

if __name__ == "__main__":
    print("=== Supabase Auth Test ===\n")
    
    # First try to login
    success, token = test_supabase_login()
    
    if not success:
        print("\n=== Creating Test User ===\n")
        if create_supabase_user():
            print("\n=== Retrying Login ===\n")
            test_supabase_login() 