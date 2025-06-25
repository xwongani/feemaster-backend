import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        self.initialized = False
        self.enabled = settings.audit_trail_enabled
        
    async def initialize(self):
        """Initialize audit service"""
        try:
            self.initialized = True
            logger.info("Audit service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize audit service: {e}")
    
    async def log_activity(self, 
                          user_id: str,
                          action: str,
                          resource_type: str,
                          resource_id: Optional[str] = None,
                          details: Optional[Dict] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> bool:
        """Log user activity"""
        try:
            if not self.enabled:
                return True
            
            audit_entry = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": json.dumps(details) if details else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.utcnow(),
                "session_id": None  # Can be added later for session tracking
            }
            
            result = await db.execute_query(
                "audit_logs",
                "insert",
                data=audit_entry
            )
            
            if result["success"]:
                logger.debug(f"Audit log created: {action} by {user_id}")
                return True
            else:
                logger.error(f"Failed to create audit log: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            return False
    
    async def log_login(self, user_id: str, success: bool, ip_address: str = None, user_agent: str = None) -> bool:
        """Log user login activity"""
        action = "login_success" if success else "login_failed"
        details = {"success": success}
        
        return await self.log_activity(
            user_id=user_id,
            action=action,
            resource_type="authentication",
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_payment(self, user_id: str, payment_id: str, action: str, details: Dict = None) -> bool:
        """Log payment-related activities"""
        return await self.log_activity(
            user_id=user_id,
            action=action,
            resource_type="payment",
            resource_id=payment_id,
            details=details
        )
    
    async def log_student_activity(self, user_id: str, student_id: str, action: str, details: Dict = None) -> bool:
        """Log student-related activities"""
        return await self.log_activity(
            user_id=user_id,
            action=action,
            resource_type="student",
            resource_id=student_id,
            details=details
        )
    
    async def log_fee_activity(self, user_id: str, fee_id: str, action: str, details: Dict = None) -> bool:
        """Log fee-related activities"""
        return await self.log_activity(
            user_id=user_id,
            action=action,
            resource_type="fee",
            resource_id=fee_id,
            details=details
        )
    
    async def log_system_activity(self, action: str, details: Dict = None) -> bool:
        """Log system-level activities"""
        return await self.log_activity(
            user_id="system",
            action=action,
            resource_type="system",
            details=details
        )
    
    async def log_data_export(self, user_id: str, export_type: str, record_count: int, details: Dict = None) -> bool:
        """Log data export activities"""
        export_details = {
            "export_type": export_type,
            "record_count": record_count,
            **details or {}
        }
        
        return await self.log_activity(
            user_id=user_id,
            action="data_export",
            resource_type="report",
            details=export_details
        )
    
    async def log_bulk_operation(self, user_id: str, operation_type: str, record_count: int, details: Dict = None) -> bool:
        """Log bulk operations"""
        bulk_details = {
            "operation_type": operation_type,
            "record_count": record_count,
            **details or {}
        }
        
        return await self.log_activity(
            user_id=user_id,
            action="bulk_operation",
            resource_type="bulk",
            details=bulk_details
        )
    
    async def get_audit_logs(self, 
                           user_id: Optional[str] = None,
                           action: Optional[str] = None,
                           resource_type: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 100,
                           offset: int = 0) -> Dict:
        """Get audit logs with filtering"""
        try:
            filters = {}
            
            if user_id:
                filters["user_id"] = user_id
            if action:
                filters["action"] = action
            if resource_type:
                filters["resource_type"] = resource_type
            if start_date:
                filters["timestamp__gte"] = start_date
            if end_date:
                filters["timestamp__lte"] = end_date
            
            result = await db.execute_query(
                "audit_logs",
                "select",
                filters=filters,
                select_fields="*",
                limit=limit,
                offset=offset,
                order_by="timestamp DESC"
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "data": result["data"],
                    "total": len(result["data"])
                }
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict:
        """Get activity summary for a specific user"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get user's activities
            activities = await self.get_audit_logs(
                user_id=user_id,
                start_date=start_date,
                limit=1000
            )
            
            if not activities["success"]:
                return activities
            
            # Analyze activities
            activity_counts = {}
            resource_counts = {}
            action_counts = {}
            
            for activity in activities["data"]:
                action = activity["action"]
                resource_type = activity["resource_type"]
                
                # Count actions
                action_counts[action] = action_counts.get(action, 0) + 1
                
                # Count resource types
                resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1
                
                # Count by day
                day = activity["timestamp"].split("T")[0]
                activity_counts[day] = activity_counts.get(day, 0) + 1
            
            return {
                "success": True,
                "user_id": user_id,
                "period_days": days,
                "total_activities": len(activities["data"]),
                "activity_by_day": activity_counts,
                "activity_by_action": action_counts,
                "activity_by_resource": resource_counts,
                "most_active_day": max(activity_counts.items(), key=lambda x: x[1]) if activity_counts else None,
                "most_common_action": max(action_counts.items(), key=lambda x: x[1]) if action_counts else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get user activity summary: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_system_activity_summary(self, days: int = 7) -> Dict:
        """Get system-wide activity summary"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get system activities
            activities = await self.get_audit_logs(
                start_date=start_date,
                limit=1000
            )
            
            if not activities["success"]:
                return activities
            
            # Analyze system activities
            user_activity = {}
            action_summary = {}
            resource_summary = {}
            
            for activity in activities["data"]:
                user_id = activity["user_id"]
                action = activity["action"]
                resource_type = activity["resource_type"]
                
                # User activity
                if user_id not in user_activity:
                    user_activity[user_id] = 0
                user_activity[user_id] += 1
                
                # Action summary
                if action not in action_summary:
                    action_summary[action] = 0
                action_summary[action] += 1
                
                # Resource summary
                if resource_type not in resource_summary:
                    resource_summary[resource_type] = 0
                resource_summary[resource_type] += 1
            
            return {
                "success": True,
                "period_days": days,
                "total_activities": len(activities["data"]),
                "unique_users": len(user_activity),
                "most_active_user": max(user_activity.items(), key=lambda x: x[1]) if user_activity else None,
                "action_summary": action_summary,
                "resource_summary": resource_summary,
                "top_actions": sorted(action_summary.items(), key=lambda x: x[1], reverse=True)[:5],
                "top_resources": sorted(resource_summary.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            logger.error(f"Failed to get system activity summary: {e}")
            return {"success": False, "error": str(e)}
    
    async def cleanup_old_logs(self) -> Dict:
        """Clean up old audit logs based on retention policy"""
        try:
            if not self.enabled:
                return {"success": True, "message": "Audit trail disabled"}
            
            cutoff_date = datetime.utcnow() - timedelta(days=settings.audit_retention_days)
            
            # Delete old logs
            result = await db.execute_query(
                "audit_logs",
                "delete",
                filters={"timestamp__lt": cutoff_date}
            )
            
            if result["success"]:
                deleted_count = result.get("deleted_count", 0)
                logger.info(f"Cleaned up {deleted_count} old audit logs")
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat()
                }
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return {"success": False, "error": str(e)}
    
    async def export_audit_logs(self, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               format: str = "json") -> Dict:
        """Export audit logs"""
        try:
            # Get logs
            logs = await self.get_audit_logs(
                start_date=start_date,
                end_date=end_date,
                limit=10000  # Large limit for export
            )
            
            if not logs["success"]:
                return logs
            
            if format.lower() == "json":
                return {
                    "success": True,
                    "format": "json",
                    "data": logs["data"],
                    "count": len(logs["data"])
                }
            elif format.lower() == "csv":
                # Convert to CSV format
                csv_data = []
                if logs["data"]:
                    # Headers
                    headers = list(logs["data"][0].keys())
                    csv_data.append(",".join(headers))
                    
                    # Data rows
                    for log in logs["data"]:
                        row = [str(log.get(header, "")) for header in headers]
                        csv_data.append(",".join(row))
                
                return {
                    "success": True,
                    "format": "csv",
                    "data": "\n".join(csv_data),
                    "count": len(logs["data"])
                }
            else:
                return {"success": False, "error": f"Unsupported format: {format}"}
                
        except Exception as e:
            logger.error(f"Failed to export audit logs: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_audit_statistics(self) -> Dict:
        """Get audit trail statistics"""
        try:
            # Get basic statistics
            total_logs = await db.execute_query(
                "audit_logs",
                "count"
            )
            
            # Get logs from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_logs = await db.execute_query(
                "audit_logs",
                "count",
                filters={"timestamp__gte": yesterday}
            )
            
            # Get unique users in last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            unique_users = await db.execute_query(
                "audit_logs",
                "select",
                filters={"timestamp__gte": week_ago},
                select_fields="DISTINCT user_id"
            )
            
            return {
                "success": True,
                "total_logs": total_logs.get("count", 0) if total_logs["success"] else 0,
                "logs_last_24h": recent_logs.get("count", 0) if recent_logs["success"] else 0,
                "unique_users_last_7d": len(unique_users["data"]) if unique_users["success"] else 0,
                "retention_days": settings.audit_retention_days,
                "enabled": self.enabled
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {"success": False, "error": str(e)}

# Initialize service
audit_service = AuditService() 