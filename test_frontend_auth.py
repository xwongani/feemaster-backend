import requests
import json
import os
import jwt
import time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
API_BASE = "http://localhost:8000/api/v1"

def test_manual_jwt():
    """Create a manual JWT for testing"""
    print("Testing with manual JWT...\n")
    
    # Create a simple JWT payload similar to what Supabase would create
    payload = {
        "sub": "test-user-id",
        "email": "admin@example.com", 
        "role": "authenticated",
        "iss": "supabase",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,  # 1 hour from now
        "iat": int(time.time()),
        "user_metadata": {
            "first_name": "Admin",
            "last_name": "User"
        },
        "app_metadata": {
            "role": "admin"
        }
    }
    
    # Sign with service key
    token = jwt.encode(payload, SUPABASE_SERVICE_KEY, algorithm="HS256")
    
    print(f"Created test token: {token[:50]}...")
    
    # Test our backend API with the manual token
    students_response = requests.get(
        f"{API_BASE}/students",
        headers={
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {token}"
        }
    )
    
    print(f"Students API Status: {students_response.status_code}")
    print(f"Students Response: {students_response.text[:300]}...")
    
    if students_response.status_code == 200:
        print("✅ API call successful with manual JWT!")
        return True, token
    else:
        print("❌ API call failed")
        return False, None

if __name__ == "__main__":
    print("=== Frontend Auth Integration Test ===\n")
    
    # Test with manual JWT 
    success, token = test_manual_jwt()
    
    if success:
        print(f"\n✅ Authentication working! You can use this token in frontend:")
        print(f"Token: {token}")
    else:
        print("\n❌ Authentication failed") 