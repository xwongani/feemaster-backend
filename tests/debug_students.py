import asyncio
from app.database import db

async def check_students():
    await db.connect()
    
    # Check total students using Supabase table query
    result1 = await db.execute_query('students', 'select', select_fields='*')
    print('All students:', result1)
    print('Total count:', len(result1.get('data', [])) if result1['success'] else 0)
    
    # Check students by status if we have data
    if result1['success'] and result1['data']:
        students = result1['data']
        statuses = {}
        for student in students:
            status = student.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        print('Students by status:', statuses)
        
        # Show first 3 students
        print('Sample students:')
        for i, student in enumerate(students[:3]):
            print(f"  {i+1}. {student.get('first_name', 'N/A')} {student.get('last_name', 'N/A')} (ID: {student.get('student_id', 'N/A')}, Status: {student.get('status', 'N/A')})")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_students()) 