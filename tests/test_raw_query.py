import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db

async def test_raw_query():
    """Test the execute_raw_query function with different queries"""
    await db.connect()
    
    print("=== Testing Raw SQL Queries ===\n")
    
    # Test 1: Simple count query
    print("1. Testing student count:")
    result = await db.execute_raw_query("SELECT COUNT(*) as total_students FROM students WHERE status = 'active'")
    print("Raw query result:", result)
    print("Type of result:", type(result))
    
    if result["success"] and result["data"]:
        print("Data:", result["data"])
        print("Type of data:", type(result["data"]))
        if result["data"].get("data"):
            print("First item:", result["data"]["data"][0] if result["data"]["data"] else "No data")
    print()
    
    # Test 2: Grade distribution
    print("2. Testing grade distribution:")
    grade_query = """
        SELECT 
            grade,
            COUNT(*) as student_count
        FROM students 
        WHERE status = 'active'
        GROUP BY grade
        ORDER BY grade
    """
    result2 = await db.execute_raw_query(grade_query)
    print("Grade distribution result:", result2)
    print()
    
    # Test 3: Recent payments
    print("3. Testing recent payments:")
    payments_query = """
        SELECT 
            p.id,
            s.first_name || ' ' || s.last_name as student_name,
            p.amount,
            p.payment_status
        FROM payments p
        JOIN students s ON p.student_id = s.id
        ORDER BY p.payment_date DESC
        LIMIT 3
    """
    result3 = await db.execute_raw_query(payments_query)
    print("Recent payments result:", result3)
    print()
    
    await db.disconnect()
    print("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_raw_query()) 