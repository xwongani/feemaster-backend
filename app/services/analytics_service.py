import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
import asyncio

from ..database import db
from ..config import settings

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.initialized = False
    
    async def initialize(self):
        """Initialize analytics service"""
        try:
            self.initialized = True
            logger.info("Analytics service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize analytics service: {e}")
    
    async def cleanup(self):
        """Cleanup analytics service resources"""
        try:
            self.cache.clear()
            self.initialized = False
            logger.info("Analytics service cleaned up")
        except Exception as e:
            logger.error(f"Error during analytics service cleanup: {e}")
    
    def _get_cache_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key for analytics data"""
        import hashlib
        key_data = f"{prefix}_{str(sorted(params.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cache_time = cache_entry.get("timestamp", 0)
        return (datetime.utcnow().timestamp() - cache_time) < self.cache_ttl
    
    async def get_payment_trends(self, period: str = "month", date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict[str, Any]:
        """Get payment trends analysis"""
        try:
            # Create materialized view for payment trends
            trends_view_query = """
                CREATE MATERIALIZED VIEW IF NOT EXISTS payment_trends AS
                SELECT 
                    DATE_TRUNC('month', payment_date) as period,
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END), 0) as completed_amount,
                    COALESCE(SUM(CASE WHEN payment_status = 'pending' THEN amount ELSE 0 END), 0) as pending_amount,
                    COALESCE(AVG(CASE WHEN payment_status = 'completed' THEN amount END), 0) as avg_amount,
                    COUNT(CASE WHEN payment_status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN payment_status = 'failed' THEN 1 END) as failed_count
                FROM payments
                GROUP BY DATE_TRUNC('month', payment_date)
                WITH DATA;
            """
            
            # Create index on materialized view
            trends_view_index = """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_trends_period ON payment_trends(period);
            """
            
            # Execute view creation
            await db.execute_raw_query(trends_view_query)
            await db.execute_raw_query(trends_view_index)
            
            # Calculate date range
            end_date = date_to or datetime.now().date()
            if period == "week":
                start_date = date_from or (end_date - timedelta(days=7))
                group_format = "DATE_TRUNC('day', payment_date)"
                date_format = "YYYY-MM-DD"
            elif period == "month":
                start_date = date_from or (end_date - timedelta(days=30))
                group_format = "DATE_TRUNC('day', payment_date)"
                date_format = "YYYY-MM-DD"
            elif period == "quarter":
                start_date = date_from or (end_date - timedelta(days=90))
                group_format = "DATE_TRUNC('month', payment_date)"
                date_format = "YYYY-MM"
            else:  # year
                start_date = date_from or (end_date - timedelta(days=365))
                group_format = "DATE_TRUNC('month', payment_date)"
                date_format = "YYYY-MM"
            
            # Query using materialized view
            trends_query = f"""
                SELECT 
                    {group_format} as period,
                    SUM(transaction_count) as transaction_count,
                    SUM(completed_amount) as completed_amount,
                    SUM(pending_amount) as pending_amount,
                    AVG(avg_amount) as avg_amount,
                    SUM(completed_count) as completed_count,
                    SUM(failed_count) as failed_count
                FROM payment_trends
                WHERE period >= '{start_date}' AND period <= '{end_date}'
                GROUP BY {group_format}
                ORDER BY period
            """
            
            result = await db.execute_raw_query(trends_query)
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch payment trends"}
            
            # Calculate growth rates
            data = result["data"]
            trends_data = {
                "period": date_format,
                "data": data,
                "summary": {
                    "total_amount": sum(float(row["completed_amount"]) for row in data),
                    "total_transactions": sum(int(row["transaction_count"]) for row in data),
                    "avg_transaction_value": sum(float(row["avg_amount"]) for row in data) / len(data) if data else 0,
                    "success_rate": (sum(int(row["completed_count"]) for row in data) / sum(int(row["transaction_count"]) for row in data) * 100) if sum(int(row["transaction_count"]) for row in data) > 0 else 0
                }
            }
            
            return {"success": True, "data": trends_data}
            
        except Exception as e:
            logger.error(f"Payment trends query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_student_analytics(self) -> Dict[str, Any]:
        """Get student analytics data"""
        try:
            if not self.initialized:
                return {"success": False, "error": "Analytics service not initialized"}
            
            # Check cache
            cache_key = self._get_cache_key("student_analytics", {})
            if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
                return self.cache[cache_key]["data"]
            
            # Query student analytics
            analytics_query = """
                SELECT 
                    s.current_grade,
                    COUNT(*) as total_students,
                    COUNT(CASE WHEN s.status = 'active' THEN 1 END) as active_students,
                    COUNT(CASE WHEN s.gender = 'male' THEN 1 END) as male_students,
                    COUNT(CASE WHEN s.gender = 'female' THEN 1 END) as female_students,
                    COALESCE(SUM(sf.amount), 0) as total_fees,
                    COALESCE(SUM(sf.paid_amount), 0) as total_paid,
                    COUNT(CASE WHEN sf.is_paid = false THEN 1 END) as students_with_outstanding,
                    AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, s.date_of_birth))) as avg_age
                FROM students s
                LEFT JOIN student_fees sf ON s.id = sf.student_id
                WHERE s.status = 'active'
                GROUP BY s.current_grade
                ORDER BY s.current_grade
            """
            
            result = await db.execute_raw_query(analytics_query)
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch student analytics"}
            
            data = result["data"]
            
            # Calculate summary statistics
            total_students = sum(int(row["total_students"]) for row in data)
            total_male = sum(int(row["male_students"]) for row in data)
            total_female = sum(int(row["female_students"]) for row in data)
            
            analytics_data = {
                "by_grade": data,
                "summary": {
                    "total_students": total_students,
                    "total_grades": len(data),
                    "gender_distribution": {
                        "male": total_male,
                        "female": total_female,
                        "male_percentage": (total_male / total_students * 100) if total_students > 0 else 0,
                        "female_percentage": (total_female / total_students * 100) if total_students > 0 else 0
                    },
                    "payment_statistics": {
                        "total_fees": sum(float(row["total_fees"]) for row in data),
                        "total_paid": sum(float(row["total_paid"]) for row in data),
                        "students_with_outstanding": sum(int(row["students_with_outstanding"]) for row in data)
                    }
                }
            }
            
            # Cache the result
            self.cache[cache_key] = {
                "data": {"success": True, "data": analytics_data},
                "timestamp": datetime.utcnow().timestamp()
            }
            
            return {"success": True, "data": analytics_data}
            
        except Exception as e:
            logger.error(f"Failed to get student analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_financial_analytics(self, period: str = "month") -> Dict[str, Any]:
        """Get financial analytics data"""
        try:
            if not self.initialized:
                return {"success": False, "error": "Analytics service not initialized"}
            
            # Check cache
            cache_key = self._get_cache_key("financial_analytics", {"period": period})
            if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
                return self.cache[cache_key]["data"]
            
            # Calculate date range
            end_date = datetime.now().date()
            
            if period == "week":
                start_date = end_date - timedelta(days=7)
                previous_start = start_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
                previous_start = start_date - timedelta(days=30)
            elif period == "quarter":
                start_date = end_date - timedelta(days=90)
                previous_start = start_date - timedelta(days=90)
            else:  # year
                start_date = end_date - timedelta(days=365)
                previous_start = start_date - timedelta(days=365)
            
            # Current period analytics
            current_query = f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END), 0) as total_revenue,
                    COALESCE(SUM(CASE WHEN payment_status = 'pending' THEN amount ELSE 0 END), 0) as pending_revenue,
                    COUNT(CASE WHEN payment_status = 'completed' THEN 1 END) as completed_transactions,
                    COUNT(CASE WHEN payment_status = 'failed' THEN 1 END) as failed_transactions,
                    COUNT(*) as total_transactions,
                    COALESCE(AVG(CASE WHEN payment_status = 'completed' THEN amount END), 0) as avg_transaction_value
                FROM payments 
                WHERE payment_date >= '{start_date}' AND payment_date <= '{end_date}'
            """
            
            # Previous period for comparison
            previous_query = f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END), 0) as total_revenue
                FROM payments 
                WHERE payment_date >= '{previous_start}' AND payment_date < '{start_date}'
            """
            
            # Payment method breakdown
            methods_query = f"""
                SELECT 
                    payment_method,
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(amount), 0) as total_amount
                FROM payments 
                WHERE payment_date >= '{start_date}' AND payment_date <= '{end_date}'
                AND payment_status = 'completed'
                GROUP BY payment_method
                ORDER BY total_amount DESC
            """
            
            # Execute queries
            current_result, previous_result, methods_result = await asyncio.gather(
                db.execute_raw_query(current_query),
                db.execute_raw_query(previous_query),
                db.execute_raw_query(methods_query)
            )
            
            if not all(result["success"] for result in [current_result, previous_result, methods_result]):
                return {"success": False, "error": "Failed to fetch financial analytics"}
            
            current_data = current_result["data"][0] if current_result["data"] else {}
            previous_data = previous_result["data"][0] if previous_result["data"] else {}
            methods_data = methods_result["data"]
            
            # Calculate growth rate
            current_revenue = float(current_data.get("total_revenue", 0))
            previous_revenue = float(previous_data.get("total_revenue", 0))
            growth_rate = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
            
            analytics_data = {
                "period": period,
                "current_period": {
                    "total_revenue": current_revenue,
                    "pending_revenue": float(current_data.get("pending_revenue", 0)),
                    "completed_transactions": int(current_data.get("completed_transactions", 0)),
                    "failed_transactions": int(current_data.get("failed_transactions", 0)),
                    "total_transactions": int(current_data.get("total_transactions", 0)),
                    "avg_transaction_value": float(current_data.get("avg_transaction_value", 0)),
                    "success_rate": (int(current_data.get("completed_transactions", 0)) / int(current_data.get("total_transactions", 1)) * 100)
                },
                "growth": {
                    "revenue_growth": growth_rate,
                    "previous_revenue": previous_revenue
                },
                "payment_methods": methods_data
            }
            
            # Cache the result
            self.cache[cache_key] = {
                "data": {"success": True, "data": analytics_data},
                "timestamp": datetime.utcnow().timestamp()
            }
            
            return {"success": True, "data": analytics_data}
            
        except Exception as e:
            logger.error(f"Failed to get financial analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_predictive_analytics(self) -> Dict[str, Any]:
        """Get predictive analytics and forecasts"""
        try:
            if not self.initialized:
                return {"success": False, "error": "Analytics service not initialized"}
            
            # Simple trend-based predictions
            # In production, use more sophisticated ML models
            
            # Get last 3 months of data for trend analysis
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            trend_query = f"""
                SELECT 
                    DATE_TRUNC('month', payment_date) as month,
                    COALESCE(SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END), 0) as revenue
                FROM payments 
                WHERE payment_date >= '{start_date}' AND payment_date <= '{end_date}'
                GROUP BY DATE_TRUNC('month', payment_date)
                ORDER BY month
            """
            
            result = await db.execute_raw_query(trend_query)
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch trend data"}
            
            data = result["data"]
            
            if len(data) < 2:
                return {"success": True, "data": {"message": "Insufficient data for predictions"}}
            
            # Simple linear trend calculation
            revenues = [float(row["revenue"]) for row in data]
            if len(revenues) >= 2:
                # Calculate average growth rate
                growth_rates = []
                for i in range(1, len(revenues)):
                    if revenues[i-1] > 0:
                        growth = (revenues[i] - revenues[i-1]) / revenues[i-1]
                        growth_rates.append(growth)
                
                avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
                
                # Predict next month
                last_revenue = revenues[-1]
                predicted_revenue = last_revenue * (1 + avg_growth)
                
                # Outstanding fees prediction
                outstanding_query = """
                    SELECT 
                        COALESCE(SUM(amount - paid_amount), 0) as total_outstanding
                    FROM student_fees 
                    WHERE is_paid = false
                """
                
                outstanding_result = await db.execute_raw_query(outstanding_query)
                total_outstanding = float(outstanding_result["data"][0]["total_outstanding"]) if outstanding_result["success"] else 0
                
                # Estimated collection rate (based on historical data)
                collection_rate = 0.75  # 75% collection rate assumption
                predicted_collections = total_outstanding * collection_rate
                
                predictions_data = {
                    "revenue_forecast": {
                        "next_month_predicted": predicted_revenue,
                        "growth_rate": avg_growth * 100,
                        "confidence": "medium",  # Simple classification
                        "historical_data": data
                    },
                    "collection_forecast": {
                        "total_outstanding": total_outstanding,
                        "predicted_collections": predicted_collections,
                        "estimated_collection_rate": collection_rate * 100
                    },
                    "recommendations": self._generate_recommendations(avg_growth, total_outstanding, predicted_revenue)
                }
                
                return {"success": True, "data": predictions_data}
            
            return {"success": True, "data": {"message": "Insufficient data for trend analysis"}}
            
        except Exception as e:
            logger.error(f"Failed to get predictive analytics: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_recommendations(self, growth_rate: float, outstanding: float, predicted_revenue: float) -> List[str]:
        """Generate recommendations based on analytics"""
        recommendations = []
        
        if growth_rate < 0:
            recommendations.append("Revenue is declining. Consider reviewing fee structure and collection processes.")
        elif growth_rate < 0.05:
            recommendations.append("Revenue growth is slow. Explore strategies to increase enrollment or fees.")
        else:
            recommendations.append("Revenue is growing well. Maintain current strategies.")
        
        if outstanding > predicted_revenue * 0.5:
            recommendations.append("High outstanding fees detected. Implement aggressive collection strategies.")
        
        if outstanding > 0:
            recommendations.append("Send payment reminders to students with outstanding fees.")
            recommendations.append("Consider offering payment plans for large outstanding amounts.")
        
        return recommendations
    
    async def clear_cache(self):
        """Clear analytics cache"""
        self.cache.clear()
        logger.info("Analytics cache cleared")

# Create global analytics service instance
analytics_service = AnalyticsService() 