import asyncio
import bcrypt
from app.database import db

async def create_admin_user():
    """Create a default admin user for testing"""
    try:
        await db.connect()
        
        # Check if admin user already exists
        existing = await db.execute_query(
            "users",
            "select",
            filters={"email": "admin@feemaster.edu"},
            select_fields="*"
        )
        
        if existing["success"] and existing["data"]:
            print("Admin user already exists:")
            print(f"Email: {existing['data'][0]['email']}")
            print(f"Role: {existing['data'][0]['role']}")
            print(f"Active: {existing['data'][0]['is_active']}")
            return
        
        # Hash password
        password = "admin123"
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Create admin user
        user_data = {
            "email": "admin@feemaster.edu",
            "password_hash": password_hash,
            "first_name": "Admin",
            "last_name": "User",
            "role": "admin",
            "is_active": True
        }
        
        result = await db.execute_query("users", "insert", data=user_data)
        
        if result["success"]:
            print("Admin user created successfully!")
            print(f"Email: admin@feemaster.edu")
            print(f"Password: admin123")
            print(f"Role: admin")
        else:
            print(f"Failed to create admin user: {result}")
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_admin_user())