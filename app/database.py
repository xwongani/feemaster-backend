import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
from .config import settings
import asyncpg
from contextlib import asynccontextmanager
import time
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
QUERY_DURATION = Histogram('query_duration_seconds', 'Time spent executing queries', ['operation'])
QUERY_COUNT = Counter('query_count_total', 'Total number of queries executed', ['operation', 'status'])
ACTIVE_CONNECTIONS = Gauge('active_db_connections', 'Number of active database connections')
SLOW_QUERY_THRESHOLD = 1.0  # seconds

class Database:
    def __init__(self):
        self.supabase_client = None
        self.pool = None
        self._connection_lock = asyncio.Lock()
        self._query_log = []
        self._max_query_log_size = 1000
        
    async def connect(self):
        """Initialize database connections"""
        try:
            # Initialize Supabase connection only if URL is provided
            if settings.supabase_url and settings.supabase_service_key:
                try:
                    from supabase import create_client, Client
                    self.supabase_client = create_client(
                        settings.supabase_url,
                        settings.supabase_service_key
                    )
                    logger.info("Supabase connection initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize Supabase connection: {e}")
                    self.supabase_client = None
            
            # Initialize connection pool if database_url is provided
            if settings.database_url:
                self.pool = await asyncpg.create_pool(
                    settings.database_url,
                    min_size=5,
                    max_size=settings.database_pool_size,
                    max_queries=50000,
                    max_inactive_connection_lifetime=300.0,
                    command_timeout=60.0,
                    statement_cache_size=100
                )
                
                # Set up connection monitoring
                asyncio.create_task(self._monitor_connections())
                logger.info("PostgreSQL connection pool initialized")
            else:
                logger.warning("No DATABASE_URL provided - using Supabase only")
            
            logger.info("Database connections initialized successfully")
                
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    async def initialize(self):
        """Initialize database connections (alias for connect)"""
        await self.connect()

    async def check_connection(self) -> Dict[str, Any]:
        """Check database connection status"""
        try:
            if self.pool:
                async with self.get_connection() as conn:
                    await conn.fetchval("SELECT 1")
                return {"status": "connected", "type": "postgresql"}
            elif self.supabase_client:
                # Simple test query for Supabase
                result = self.supabase_client.table("schools").select("id").limit(1).execute()
                return {"status": "connected", "type": "supabase"}
            else:
                return {"status": "disconnected", "type": "none"}
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return {"status": "error", "type": "unknown", "error": str(e)}

    async def close(self):
        """Close database connections"""
        try:
            if self.pool:
                await self.pool.close()
                logger.info("PostgreSQL connection pool closed")
            if self.supabase_client:
                # Supabase client doesn't need explicit closing
                self.supabase_client = None
                logger.info("Supabase connection closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

    async def _monitor_connections(self):
        """Monitor database connections"""
        while True:
            try:
                if self.pool:
                    ACTIVE_CONNECTIONS.set(len(self.pool._holders))
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Connection monitoring failed: {e}")

    def _log_query(self, operation: str, query: str, duration: float, status: str):
        """Log query execution details"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'query': query,
            'duration': duration,
            'status': status
        }
        
        self._query_log.append(log_entry)
        if len(self._query_log) > self._max_query_log_size:
            self._query_log.pop(0)
            
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(f"Slow query detected: {duration:.2f}s - {query}")

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
        """Execute database operations with monitoring"""
        start_time = time.time()
        try:
            # Ensure we have a connection
            if not self.pool and not self.supabase_client:
                await self.connect()
            
            # Use direct PostgreSQL connection if available
            if self.pool:
                async with self.get_connection() as conn:
                    query = self._build_query(
                        table, operation, data, filters,
                        select_fields, limit, offset, order_by, join_tables
                    )
                    result = await conn.fetch(query)
                    duration = time.time() - start_time
                    self._log_query(operation, query, duration, "success")
                    QUERY_DURATION.labels(operation=operation).observe(duration)
                    QUERY_COUNT.labels(operation=operation, status="success").inc()
                    return {"success": True, "data": [dict(row) for row in result]}
            
            # Use Supabase for simple operations if available
            if self.supabase_client:
                query = self.supabase_client.table(table)
                
                if operation == "select":
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
                    duration = time.time() - start_time
                    self._log_query(operation, str(query), duration, "success")
                    QUERY_DURATION.labels(operation=operation).observe(duration)
                    QUERY_COUNT.labels(operation=operation, status="success").inc()
                    return {"success": True, "data": result.data}
                    
                elif operation == "insert":
                    result = query.insert(data).execute()
                    duration = time.time() - start_time
                    self._log_query(operation, str(query), duration, "success")
                    QUERY_DURATION.labels(operation=operation).observe(duration)
                    QUERY_COUNT.labels(operation=operation, status="success").inc()
                    return {"success": True, "data": result.data}
                    
                elif operation == "update":
                    query = query.update(data)
                    if filters:
                        query = self._apply_filters(query, filters)
                    result = query.execute()
                    duration = time.time() - start_time
                    self._log_query(operation, str(query), duration, "success")
                    QUERY_DURATION.labels(operation=operation).observe(duration)
                    QUERY_COUNT.labels(operation=operation, status="success").inc()
                    return {"success": True, "data": result.data}
                    
                elif operation == "delete":
                    if filters:
                        query = self._apply_filters(query, filters)
                    result = query.delete().execute()
                    duration = time.time() - start_time
                    self._log_query(operation, str(query), duration, "success")
                    QUERY_DURATION.labels(operation=operation).observe(duration)
                    QUERY_COUNT.labels(operation=operation, status="success").inc()
                    return {"success": True, "data": result.data}
            
            # If neither PostgreSQL nor Supabase is available
            raise Exception("No database connection available")
                
        except Exception as e:
            duration = time.time() - start_time
            self._log_query(operation, str(query) if 'query' in locals() else "N/A", duration, "error")
            QUERY_DURATION.labels(operation=operation).observe(duration)
            QUERY_COUNT.labels(operation=operation, status="error").inc()
            logger.error(f"Query execution failed: {e}")
            return {"success": False, "error": str(e), "data": []}

    async def get_query_stats(self) -> Dict[str, Any]:
        """Get query execution statistics"""
        return {
            "total_queries": len(self._query_log),
            "slow_queries": len([q for q in self._query_log if q['duration'] > SLOW_QUERY_THRESHOLD]),
            "average_duration": sum(q['duration'] for q in self._query_log) / len(self._query_log) if self._query_log else 0,
            "recent_slow_queries": [q for q in self._query_log[-10:] if q['duration'] > SLOW_QUERY_THRESHOLD]
        }
    
    async def disconnect(self):
        """Close database connections"""
        try:
            if self.pool:
                await self.pool.close()
                logger.info("Database pool closed")
            
            # Supabase client doesn't need explicit disconnection
            logger.info("Database connections closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            raise Exception("Database pool not initialized")
            
        async with self._connection_lock:
            conn = await self.pool.acquire()
            try:
                yield conn
            finally:
                await self.pool.release(conn)
    
    def _build_query(
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
    ) -> str:
        """Build SQL query for direct PostgreSQL execution"""
        if operation == "select":
            query = f"SELECT {select_fields} FROM {table}"
            
            if join_tables:
                for join_table in join_tables:
                    query += f" LEFT JOIN {join_table} ON {table}.id = {join_table}.{table}_id"
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    if "__" in key:
                        field, operator = key.split("__", 1)
                        if operator == "gte":
                            conditions.append(f"{field} >= '{value}'")
                        elif operator == "lte":
                            conditions.append(f"{field} <= '{value}'")
                        elif operator == "like":
                            conditions.append(f"{field} LIKE '%{value}%'")
                        elif operator == "ilike":
                            conditions.append(f"{field} ILIKE '%{value}%'")
                        elif operator == "in":
                            conditions.append(f"{field} IN ({','.join(map(str, value))})")
                        elif operator == "neq":
                            conditions.append(f"{field} != '{value}'")
                    else:
                        conditions.append(f"{key} = '{value}'")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            if offset:
                query += f" OFFSET {offset}"
            
            return query
        
        # Add other operation types as needed
        raise NotImplementedError(f"Operation {operation} not implemented for direct PostgreSQL")
    
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
        """Get real-time dashboard statistics with caching"""
        try:
            # Use materialized view for better performance
            stats_query = """
                CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_stats AS
                WITH current_term AS (
                    SELECT id, term_name 
                    FROM academic_terms 
                    WHERE is_current = true
                    LIMIT 1
                ),
                fee_stats AS (
                    SELECT 
                        COUNT(*) as total_students,
                        SUM(CASE WHEN is_paid = true THEN 1 ELSE 0 END) as paid_students,
                        SUM(CASE WHEN is_paid = false AND due_date < CURRENT_DATE THEN 1 ELSE 0 END) as overdue_students,
                        SUM(amount) as total_fees,
                        SUM(CASE WHEN is_paid = true THEN amount ELSE 0 END) as paid_amount,
                        SUM(CASE WHEN is_paid = false AND due_date < CURRENT_DATE THEN amount ELSE 0 END) as overdue_amount
                    FROM student_fees sf
                    JOIN current_term ct ON sf.academic_term_id = ct.id
                ),
                payment_stats AS (
                    SELECT 
                        COUNT(*) as total_payments,
                        SUM(amount) as total_revenue,
                        COUNT(DISTINCT student_id) as students_paid,
                        COUNT(CASE WHEN payment_status = 'completed' THEN 1 END) as successful_payments
                    FROM payments
                    WHERE payment_date >= CURRENT_DATE - INTERVAL '30 days'
                ),
                recent_activities AS (
                    SELECT 
                        p.id,
                        p.payment_date,
                        s.student_id,
                        CONCAT(s.first_name, ' ', s.last_name) as student_name,
                        p.amount,
                        p.payment_status
                    FROM payments p
                    JOIN students s ON p.student_id = s.id
                    ORDER BY p.payment_date DESC
                    LIMIT 5
                )
                SELECT 
                    fs.*,
                    ps.*,
                    json_agg(ra.*) as recent_activities
                FROM fee_stats fs
                CROSS JOIN payment_stats ps
                CROSS JOIN recent_activities ra
                GROUP BY 
                    fs.total_students, fs.paid_students, fs.overdue_students,
                    fs.total_fees, fs.paid_amount, fs.overdue_amount,
                    ps.total_payments, ps.total_revenue, ps.students_paid,
                    ps.successful_payments;
            """
            
            # Create index on materialized view
            index_query = """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_dashboard_stats ON dashboard_stats(total_students);
            """
            
            # Execute view creation and indexing
            await self.execute_raw_query(stats_query)
            await self.execute_raw_query(index_query)
            
            # Refresh materialized view
            refresh_query = "REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard_stats;"
            await self.execute_raw_query(refresh_query)
            
            # Get stats
            result = await self.execute_raw_query("SELECT * FROM dashboard_stats;")
            
            if not result["success"] or not result["data"]:
                return {
                    "success": False,
                    "error": "Failed to fetch dashboard statistics",
                    "data": {}
                }
            
            stats = result["data"][0]
            
            # Calculate additional metrics
            stats["payment_success_rate"] = (
                stats["successful_payments"] / stats["total_payments"] * 100 
                if stats["total_payments"] > 0 else 0
            )
            
            stats["collection_rate"] = (
                stats["paid_amount"] / stats["total_fees"] * 100 
                if stats["total_fees"] > 0 else 0
            )
            
            stats["average_payment"] = (
                stats["total_revenue"] / stats["total_payments"] 
                if stats["total_payments"] > 0 else 0
            )
            
            return {
                "success": True,
                "data": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
    
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