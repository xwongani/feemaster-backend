import asyncio
import aiohttp
import json

async def test_dashboard_endpoints():
    """Test all dashboard API endpoints"""
    base_url = "http://localhost:8000/api/v1/dashboard"
    
    endpoints = [
        "/stats",
        "/grade-distribution", 
        "/quick-actions",
        "/revenue-chart?period=week"
    ]
    
    print("=== Testing Dashboard Endpoints ===\n")
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                print(f"Testing: {endpoint}")
                async with session.get(f"{base_url}{endpoint}") as response:
                    status = response.status
                    data = await response.json()
                    
                    print(f"Status: {status}")
                    print(f"Success: {data.get('success', 'N/A')}")
                    print(f"Message: {data.get('message', 'N/A')}")
                    
                    if data.get('success') and data.get('data'):
                        if endpoint == "/stats":
                            stats = data['data']
                            print(f"Students: {stats.get('total_students', 'N/A')}")
                            print(f"Collections: K {stats.get('total_collections', 'N/A')}")
                            print(f"Activities: {len(stats.get('recent_activities', []))}")
                        elif endpoint == "/grade-distribution":
                            grades = data['data']
                            print(f"Grades found: {len(grades)}")
                            for grade in grades:
                                print(f"  {grade['grade']}: {grade['students']} students ({grade['progress']}% paid)")
                        elif endpoint == "/quick-actions":
                            actions = data['data']
                            print(f"Actions: {len(actions)}")
                            for action in actions:
                                count_text = f" ({action['count']})" if action.get('count') else ""
                                print(f"  {action['title']}{count_text}")
                        elif "/revenue-chart" in endpoint:
                            chart = data['data']
                            print(f"Chart labels: {len(chart.get('labels', []))}")
                            print(f"Datasets: {len(chart.get('datasets', []))}")
                    
                    print("-" * 50)
                    
            except Exception as e:
                print(f"Error testing {endpoint}: {e}")
                print("-" * 50)
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_dashboard_endpoints()) 