import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
from .config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase_client = None
        
    async def connect(self):
        """Initialize Supabase connection"""
        try:
            from supabase import create_client, Client
            
            self.supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            logger.info("Connected to Supabase")
                
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close database connections"""
        if self.supabase_client:
            # Supabase client doesn't need explicit disconnection
            logger.info("Supabase connection closed")
        
    async def execute_query(
        self,
        table: str,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        select_fields: str = "*",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        join_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute database operations using Supabase"""
        try:
            if not self.supabase_client:
                await self.connect()
            
            query = self.supabase_client.table(table)
            
            if operation == "select":
                # Handle joins for complex queries
                if join_tables:
                    select_fields = self._build_join_select(table, join_tables, select_fields)
                
                query = query.select(select_fields)
                
                if filters:
                    query = self._apply_filters(query, filters)
                
                if order_by:
                    query = query.order(order_by)
                
                if limit:
                    query = query.limit(limit)
                
                if offset:
                    query = query.offset(offset)
                
                result = query.execute()
                return {"success": True, "data": result.data}
                
            elif operation == "insert":
                result = query.insert(data).execute()
                return {"success": True, "data": result.data}
                
            elif operation == "update":
                query = query.update(data)
                if filters:
                    query = self._apply_filters(query, filters)
                result = query.execute()
                return {"success": True, "data": result.data}
                
            elif operation == "delete":
                if filters:
                    query = self._apply_filters(query, filters)
                result = query.delete().execute()
                return {"success": True, "data": result.data}
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {"success": False, "error": str(e), "data": []}
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to Supabase query"""
        for key, value in filters.items():
            if "__" in key:
                field, operator = key.split("__", 1)
                if operator == "gte":
                    query = query.gte(field, value)
                elif operator == "lte":
                    query = query.lte(field, value)
                elif operator == "like":
                    query = query.like(field, f"%{value}%")
                elif operator == "ilike":
                    query = query.ilike(field, f"%{value}%")
                elif operator == "in":
                    query = query.in_(field, value)
                elif operator == "neq":
                    query = query.neq(field, value)
            else:
                query = query.eq(key, value)
        return query
    
    def _build_join_select(self, table: str, join_tables: List[str], select_fields: str) -> str:
        """Build select fields for joined tables"""
        if select_fields == "*":
            # Build comprehensive select for common joins
            if table == "students" and "parents" in join_tables:
                return """
                    *,
                    parent_student_links(
                        parent_id,
                        relationship,
                        is_primary_contact,
                        parents(*)
                    )
                """
            elif table == "payments" and "students" in join_tables:
                return """
                    *,
                    students(student_id, first_name, last_name, grade)
                """
            elif table == "student_fees" and "students" in join_tables:
                return """
                    *,
                    students(student_id, first_name, last_name, grade),
                    fee_types(name, fee_type),
                    academic_years(year_name),
                    academic_terms(term_name)
                """
        return select_fields
    
    async def execute_raw_query(self, query: str, params: List[Any] = None) -> Dict[str, Any]:
        """Execute raw SQL query using Supabase RPC"""
        try:
            if not self.supabase_client:
                await self.connect()
            
            # For raw SQL queries, we'll use Supabase RPC function
            # You'll need to create this function in your Supabase
            result = self.supabase_client.rpc('execute_sql', {
                'query': query,
                'params': params or []
            }).execute()
            
            return {"success": True, "data": result.data}
            
        except Exception as e:
            logger.error(f"Raw query failed: {e}")
            return {"success": False, "error": str(e), "data": []}
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics from actual schema"""
        try:
            # Get total active students using proper COUNT query
            students_result = await self.execute_raw_query("""
                SELECT COUNT(*) as total_students
                FROM students 
                WHERE status = 'active'
            """)
            
            # Get current academic year and term
            current_year = await self.execute_query(
                "academic_years",
                "select",
                filters={"is_current": True},
                select_fields="id, year_name"
            )
            
            current_term = await self.execute_query(
                "academic_terms",
                "select", 
                filters={"is_current": True},
                select_fields="id, term_name"
            )
            
            # Get total collections this month
            collections_result = await self.execute_raw_query("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM payments 
                WHERE payment_status = 'completed' 
                AND DATE_TRUNC('month', payment_date) = DATE_TRUNC('month', CURRENT_DATE)
            """)
            
            # Get pending payments
            pending_result = await self.execute_raw_query("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM student_fees 
                WHERE is_paid = false
            """)
            
            # Get receipts generated this month
            receipts_result = await self.execute_raw_query("""
                SELECT COUNT(*) as count
                FROM payment_receipts 
                WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """)
            
            # Get recent activities
            activities_result = await self.execute_raw_query("""
                SELECT 
                    p.id,
                    p.payment_date as datetime,
                    s.first_name || ' ' || s.last_name as student_name,
                    s.student_id,
                    UPPER(LEFT(s.first_name, 1)) || UPPER(LEFT(s.last_name, 1)) as initials,
                    'Payment' as payment_type,
                    p.amount,
                    DATE(p.payment_date) as date,
                    p.payment_status as status
                FROM payments p
                JOIN students s ON p.student_id = s.id
                ORDER BY p.payment_date DESC
                LIMIT 10
            """)
            
            total_students = students_result["data"]["data"][0]["total_students"] if students_result["success"] and students_result["data"]["data"] else 0
            total_collections = collections_result["data"]["data"][0]["total"] if collections_result["success"] and collections_result["data"]["data"] else 0
            pending_payments = pending_result["data"]["data"][0]["total"] if pending_result["success"] and pending_result["data"]["data"] else 0
            receipts_generated = receipts_result["data"]["data"][0]["count"] if receipts_result["success"] and receipts_result["data"]["data"] else 0
            recent_activities = activities_result["data"]["data"] if activities_result["success"] and activities_result["data"]["data"] else []
            
            collection_rate = 0
            if total_collections + pending_payments > 0:
                collection_rate = (total_collections / (total_collections + pending_payments)) * 100
            
            return {
                "success": True,
                "data": {
                    "total_students": total_students,
                    "total_collections": float(total_collections),
                    "pending_payments": float(pending_payments),
                    "receipts_generated": receipts_generated,
                    "collection_rate": collection_rate,
                    "recent_activities": recent_activities,
                    "current_academic_year": current_year["data"][0]["year_name"] if current_year["success"] and current_year["data"] else "2024/2025",
                    "current_academic_term": current_term["data"][0]["term_name"] if current_term["success"] and current_term["data"] else "Term 1"
                }
            }
        except Exception as e:
            logger.error(f"Dashboard stats query failed: {e}")
            return {"success": False, "error": str(e), "data": {}}
    
    async def get_financial_summary(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get financial summary data from actual schema"""
        try:
            date_filter = ""
            if date_from and date_to:
                date_filter = f"AND payment_date BETWEEN '{date_from}' AND '{date_to}'"
            
            query = f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END), 0) as collected,
                    COALESCE(SUM(CASE WHEN payment_status = 'pending' THEN amount ELSE 0 END), 0) as pending,
                    COUNT(CASE WHEN payment_status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN payment_status = 'pending' THEN 1 END) as pending_count
                FROM payments 
                WHERE 1=1 {date_filter}
            """
            
            result = await self.execute_raw_query(query)
            if result["success"] and result["data"]:
                data = result["data"][0]
                total_revenue = float(data["collected"]) + float(data["pending"])
                collection_rate = (float(data["collected"]) / total_revenue * 100) if total_revenue > 0 else 0
                
                return {
                    "success": True,
                    "data": {
                        "total_revenue": total_revenue,
                        "collected": float(data["collected"]),
                        "outstanding": float(data["pending"]),
                        "collection_rate": collection_rate,
                        "trends": {
                            "collections": 12.5,  # Calculate actual trends
                            "outstanding": 5.3,
                            "collection_rate": 3.2
                        }
                    }
                }
            
            return {"success": False, "error": "No data found", "data": {}}
            
        except Exception as e:
            logger.error(f"Financial summary query failed: {e}")
            return {"success": False, "error": str(e), "data": {}}
    
    async def get_school_settings(self) -> Dict[str, Any]:
        """Get school settings from database"""
        try:
            result = await self.execute_query(
                "school_settings",
                "select",
                select_fields="""
                    *,
                    academic_years!current_academic_year_id(year_name),
                    academic_terms!current_academic_term_id(term_name)
                """,
                limit=1
            )
            
            if result["success"] and result["data"]:
                return {"success": True, "data": result["data"][0]}
            else:
                # Return default settings if none exist
                return {
                    "success": True,
                    "data": {
                        "school_name": settings.default_school_name,
                        "email": settings.default_school_email,
                        "phone": settings.default_school_phone,
                        "address": settings.default_school_address,
                        "currency": settings.default_currency,
                        "timezone": settings.default_timezone
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get school settings: {e}")
            return {"success": False, "error": str(e), "data": {}}
    
    async def get_current_academic_context(self) -> Dict[str, Any]:
        """Get current academic year and term"""
        try:
            year_result = await self.execute_query(
                "academic_years",
                "select",
                filters={"is_current": True, "is_active": True},
                select_fields="id, year_name"
            )
            
            term_result = await self.execute_query(
                "academic_terms", 
                "select",
                filters={"is_current": True, "is_active": True},
                select_fields="id, term_name, academic_year_id"
            )
            
            return {
                "success": True,
                "data": {
                    "academic_year": year_result["data"][0] if year_result["success"] and year_result["data"] else None,
                    "academic_term": term_result["data"][0] if term_result["success"] and term_result["data"] else None
                }
            }
        except Exception as e:
            logger.error(f"Failed to get academic context: {e}")
            return {"success": False, "error": str(e), "data": {}}

# Create database instance
db = Database() 