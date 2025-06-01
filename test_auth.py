import requests
import json

API_BASE = "http://localhost:8000/api/v1"

def test_auth_flow():
    print("Testing authentication flow...\n")
    
    # Test login
    login_data = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    response = requests.post(
        f"{API_BASE}/auth/login",
        headers={"Content-Type": "application/json"},
        data=json.dumps(login_data)
    )
    
    print(f"Login Status: {response.status_code}")
    print(f"Login Response: {response.text[:200]}...")
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and result.get("data", {}).get("access_token"):
            token = result["data"]["access_token"]
            print(f"Token obtained: {token[:50]}...")
            
            # Test students API with token
            students_response = requests.get(
                f"{API_BASE}/students",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                }
            )
            
            print(f"\nStudents API Status: {students_response.status_code}")
            print(f"Students Response: {students_response.text[:300]}...")
            
            return True, token
        else:
            print("Login failed: No token in response")
            return False, None
    else:
        print("Login failed")
        return False, None

if __name__ == "__main__":
    test_auth_flow() 