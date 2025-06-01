from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from datetime import datetime
import logging

from ..models import SystemSettings, PaymentSettings, NotificationSettings, UserCreate, APIResponse
from ..database import db
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/general")
async def get_general_settings(current_user: dict = Depends(get_current_user)):
    """Get general system settings"""
    try:
        # Mock settings data - in production, fetch from database
        settings = {
            "school_name": "Fee Master Academy",
            "school_email": "info@feemaster.edu",
            "school_phone": "+260 97 123 4567",
            "school_address": "123 Education Street, Lusaka, Zambia",
            "academic_year": "2024/2025",
            "current_term": "Term 1",
            "currency": "ZMW",
            "timezone": "Africa/Lusaka",
            "date_format": "DD/MM/YYYY",
            "time_format": "24h",
            "language": "en"
        }
        
        return APIResponse(
            success=True,
            message="General settings retrieved successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch general settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/general")
async def update_general_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update general system settings"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # In production, validate and save to database
        # await db.execute_query("settings", "update", data=settings)
        
        return APIResponse(
            success=True,
            message="General settings updated successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to update general settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-options")
async def get_payment_settings(current_user: dict = Depends(get_current_user)):
    """Get payment settings"""
    try:
        settings = {
            "accept_cash": True,
            "accept_bank_transfer": True,
            "accept_mobile_money": True,
            "accept_credit_card": False,
            "accept_debit_card": True,
            "accept_cheque": False,
            "late_fee_percentage": 5.0,
            "grace_period_days": 7,
            "auto_reminders": True,
            "reminder_frequency": "weekly",
            "payment_confirmation": True,
            "receipt_generation": True
        }
        
        return APIResponse(
            success=True,
            message="Payment settings retrieved successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch payment settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/payment-options")
async def update_payment_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update payment settings"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Validate settings
        if "late_fee_percentage" in settings:
            if not 0 <= settings["late_fee_percentage"] <= 100:
                raise HTTPException(
                    status_code=400,
                    detail="Late fee percentage must be between 0 and 100"
                )
        
        if "grace_period_days" in settings:
            if not 0 <= settings["grace_period_days"] <= 365:
                raise HTTPException(
                    status_code=400,
                    detail="Grace period must be between 0 and 365 days"
                )
        
        return APIResponse(
            success=True,
            message="Payment settings updated successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to update payment settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications")
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    """Get notification settings"""
    try:
        settings = {
            "email_notifications": True,
            "sms_notifications": True,
            "whatsapp_notifications": True,
            "push_notifications": False,
            "payment_confirmations": True,
            "payment_reminders": True,
            "overdue_notifications": True,
            "receipt_delivery": True,
            "system_alerts": True,
            "maintenance_notifications": True,
            "reminder_schedule": {
                "first_reminder": 3,  # days before due date
                "second_reminder": 1,  # days before due date
                "overdue_reminder": 7   # days after due date
            }
        }
        
        return APIResponse(
            success=True,
            message="Notification settings retrieved successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/notifications")
async def update_notification_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update notification settings"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return APIResponse(
            success=True,
            message="Notification settings updated successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get system users"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Mock users data - in production, fetch from database
        users = [
            {
                "id": "1",
                "first_name": "John",
                "last_name": "Admin",
                "email": "admin@feemaster.edu",
                "role": "admin",
                "employee_id": "EMP001",
                "phone": "+260 97 111 1111",
                "is_active": True,
                "last_login": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "2",
                "first_name": "Jane",
                "last_name": "Finance",
                "email": "finance@feemaster.edu",
                "role": "finance_manager",
                "employee_id": "EMP002",
                "phone": "+260 97 222 2222",
                "is_active": True,
                "last_login": "2024-01-15T09:15:00Z",
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "3",
                "first_name": "Mike",
                "last_name": "Student Affairs",
                "email": "student.affairs@feemaster.edu",
                "role": "teacher",
                "employee_id": "EMP003",
                "phone": "+260 97 333 3333",
                "is_active": True,
                "last_login": "2024-01-14T16:45:00Z",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        return APIResponse(
            success=True,
            message="Users retrieved successfully",
            data=users
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new user"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # In production, create user in database
        # result = await db.execute_query("users", "insert", data=user_data.dict())
        
        return APIResponse(
            success=True,
            message="User created successfully",
            data={"user_id": "new_user_id"}
        )
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backup")
async def get_backup_settings(current_user: dict = Depends(get_current_user)):
    """Get backup and data settings"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        settings = {
            "auto_backup": True,
            "backup_frequency": "daily",
            "backup_time": "02:00",
            "backup_retention": 30,  # days
            "backup_location": "cloud",
            "last_backup": "2024-01-15T02:00:00Z",
            "backup_size": "2.5 GB",
            "data_retention": {
                "payments": 7,  # years
                "students": 10,  # years
                "logs": 2  # years
            }
        }
        
        return APIResponse(
            success=True,
            message="Backup settings retrieved successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch backup settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backup/manual")
async def create_manual_backup(current_user: dict = Depends(get_current_user)):
    """Create manual backup"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Mock backup creation
        backup_result = {
            "backup_id": "backup_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            "created_at": datetime.utcnow().isoformat(),
            "size": "2.5 GB",
            "status": "completed",
            "download_url": "/api/v1/settings/backup/download/backup_20240115_143000"
        }
        
        return APIResponse(
            success=True,
            message="Manual backup created successfully",
            data=backup_result
        )
        
    except Exception as e:
        logger.error(f"Failed to create manual backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/appearance")
async def get_appearance_settings(current_user: dict = Depends(get_current_user)):
    """Get appearance settings"""
    try:
        settings = {
            "theme": "light",
            "primary_color": "#3B82F6",
            "secondary_color": "#10B981",
            "logo_url": "/assets/logo.png",
            "favicon_url": "/assets/favicon.ico",
            "compact_mode": False,
            "sidebar_collapsed": False,
            "show_animations": True,
            "font_size": "medium"
        }
        
        return APIResponse(
            success=True,
            message="Appearance settings retrieved successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch appearance settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/appearance")
async def update_appearance_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update appearance settings"""
    try:
        return APIResponse(
            success=True,
            message="Appearance settings updated successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to update appearance settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system")
async def get_system_settings(current_user: dict = Depends(get_current_user)):
    """Get system settings"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        settings = {
            "maintenance_mode": False,
            "api_rate_limiting": True,
            "session_timeout": 30,  # minutes
            "password_policy": {
                "min_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_symbols": False
            },
            "security": {
                "two_factor_auth": False,
                "login_attempts": 5,
                "lockout_duration": 15  # minutes
            },
            "system_info": {
                "version": "2.0.0",
                "database_version": "PostgreSQL 14.2",
                "uptime": "15 days, 3 hours",
                "last_update": "2024-01-01T00:00:00Z"
            }
        }
        
        return APIResponse(
            success=True,
            message="System settings retrieved successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/system")
async def update_system_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update system settings"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return APIResponse(
            success=True,
            message="System settings updated successfully",
            data=settings
        )
        
    except Exception as e:
        logger.error(f"Failed to update system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 