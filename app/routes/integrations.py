from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from datetime import datetime
import logging

from ..models import Integration, IntegrationConfig, APIResponse
from ..database import db
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])

@router.get("/")
async def get_integrations(current_user: dict = Depends(get_current_user)):
    """Get all integrations with their status"""
    try:
        # Mock integration data - in production, this would come from database
        integrations = [
            {
                "id": "quickbooks",
                "name": "QuickBooks",
                "type": "accounting",
                "status": "not_connected",
                "description": "Sync financial data with QuickBooks",
                "last_sync": None,
                "config": {},
                "features": ["Financial sync", "Automated exports", "Real-time updates"]
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp Business",
                "type": "messaging",
                "status": "connected",
                "description": "Send notifications via WhatsApp",
                "last_sync": "2024-01-15T10:30:00Z",
                "config": {"phone_number": "+260971234567"},
                "features": ["Payment notifications", "Fee reminders", "Bulk messaging"]
            },
            {
                "id": "sms_gateway",
                "name": "SMS Gateway",
                "type": "messaging",
                "status": "error",
                "description": "Send SMS notifications to parents",
                "last_sync": None,
                "config": {},
                "features": ["SMS notifications", "Bulk SMS", "Delivery reports"],
                "error_message": "API key expired"
            },
            {
                "id": "email_service",
                "name": "Email Service",
                "type": "messaging",
                "status": "connected",
                "description": "Send email notifications and receipts",
                "last_sync": "2024-01-15T09:15:00Z",
                "config": {"smtp_host": "smtp.gmail.com"},
                "features": ["Email receipts", "Payment confirmations", "Automated reminders"]
            }
        ]
        
        return APIResponse(
            success=True,
            message="Integrations retrieved successfully",
            data=integrations
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{integration_id}")
async def get_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific integration details"""
    try:
        # Mock data - in production, fetch from database
        integration_details = {
            "quickbooks": {
                "id": "quickbooks",
                "name": "QuickBooks",
                "type": "accounting",
                "status": "not_connected",
                "description": "Sync financial data with QuickBooks",
                "setup_instructions": [
                    "Create QuickBooks developer account",
                    "Generate API credentials",
                    "Configure webhook endpoints",
                    "Test connection"
                ],
                "config_fields": [
                    {"name": "client_id", "type": "text", "required": True},
                    {"name": "client_secret", "type": "password", "required": True},
                    {"name": "environment", "type": "select", "options": ["sandbox", "production"]}
                ]
            },
            "whatsapp": {
                "id": "whatsapp",
                "name": "WhatsApp Business",
                "type": "messaging",
                "status": "connected",
                "description": "Send notifications via WhatsApp",
                "config": {"phone_number": "+260971234567", "api_key": "***hidden***"},
                "activity_log": [
                    {"timestamp": "2024-01-15T10:30:00Z", "action": "Message sent", "details": "Payment reminder to 5 parents"},
                    {"timestamp": "2024-01-15T09:15:00Z", "action": "Connection tested", "details": "API connection successful"}
                ]
            }
        }
        
        if integration_id not in integration_details:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return APIResponse(
            success=True,
            message="Integration details retrieved successfully",
            data=integration_details[integration_id]
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch integration details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{integration_id}/connect")
async def connect_integration(
    integration_id: str,
    config: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Connect an integration with provided configuration"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Mock connection logic - in production, implement actual integration
        if integration_id == "quickbooks":
            # Validate QuickBooks credentials
            required_fields = ["client_id", "client_secret", "environment"]
            for field in required_fields:
                if field not in config:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required field: {field}"
                    )
            
            # Mock connection test
            connection_result = {
                "status": "connected",
                "message": "Successfully connected to QuickBooks",
                "last_sync": datetime.utcnow().isoformat()
            }
            
        elif integration_id == "whatsapp":
            # Validate WhatsApp configuration
            required_fields = ["api_key", "phone_number"]
            for field in required_fields:
                if field not in config:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required field: {field}"
                    )
            
            connection_result = {
                "status": "connected",
                "message": "Successfully connected to WhatsApp Business",
                "last_sync": datetime.utcnow().isoformat()
            }
            
        elif integration_id == "sms_gateway":
            # Validate SMS Gateway configuration
            required_fields = ["api_key", "sender_id"]
            for field in required_fields:
                if field not in config:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required field: {field}"
                    )
            
            connection_result = {
                "status": "connected",
                "message": "Successfully connected to SMS Gateway",
                "last_sync": datetime.utcnow().isoformat()
            }
            
        else:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # In production, save configuration to database
        # await db.execute_query("integrations", "update", ...)
        
        return APIResponse(
            success=True,
            message=connection_result["message"],
            data=connection_result
        )
        
    except Exception as e:
        logger.error(f"Integration connection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{integration_id}/disconnect")
async def disconnect_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect an integration"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Mock disconnection logic
        disconnect_result = {
            "status": "not_connected",
            "message": f"Successfully disconnected {integration_id}",
            "disconnected_at": datetime.utcnow().isoformat()
        }
        
        # In production, update database
        # await db.execute_query("integrations", "update", ...)
        
        return APIResponse(
            success=True,
            message=disconnect_result["message"],
            data=disconnect_result
        )
        
    except Exception as e:
        logger.error(f"Integration disconnection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Test integration connection"""
    try:
        # Mock test logic - in production, implement actual testing
        test_results = {
            "quickbooks": {
                "success": True,
                "message": "QuickBooks API connection successful",
                "response_time": "245ms",
                "details": {
                    "api_version": "v3",
                    "company_info": "Test Company",
                    "permissions": ["read", "write"]
                }
            },
            "whatsapp": {
                "success": True,
                "message": "WhatsApp Business API connection successful",
                "response_time": "156ms",
                "details": {
                    "phone_verified": True,
                    "business_profile": "Fee Master Academy",
                    "message_limit": "1000/day"
                }
            },
            "sms_gateway": {
                "success": False,
                "message": "SMS Gateway connection failed",
                "error": "Invalid API key",
                "response_time": "timeout"
            }
        }
        
        if integration_id not in test_results:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        result = test_results[integration_id]
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data=result
        )
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{integration_id}/sync")
async def sync_integration(
    integration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger integration sync"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Mock sync logic
        if integration_id == "quickbooks":
            # Mock QuickBooks sync
            sync_result = {
                "success": True,
                "message": "QuickBooks sync completed successfully",
                "synced_records": {
                    "payments": 25,
                    "customers": 12,
                    "invoices": 8
                },
                "sync_duration": "2.3s",
                "last_sync": datetime.utcnow().isoformat()
            }
        else:
            sync_result = {
                "success": True,
                "message": f"{integration_id} sync completed",
                "last_sync": datetime.utcnow().isoformat()
            }
        
        return APIResponse(
            success=sync_result["success"],
            message=sync_result["message"],
            data=sync_result
        )
        
    except Exception as e:
        logger.error(f"Integration sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{integration_id}/activity")
async def get_integration_activity(
    integration_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get integration activity log"""
    try:
        # Mock activity data
        activities = [
            {
                "id": "1",
                "timestamp": "2024-01-15T10:30:00Z",
                "action": "sync_completed",
                "status": "success",
                "details": "Synced 25 payment records",
                "duration": "2.3s"
            },
            {
                "id": "2",
                "timestamp": "2024-01-15T09:15:00Z",
                "action": "connection_test",
                "status": "success",
                "details": "API connection verified",
                "duration": "0.5s"
            },
            {
                "id": "3",
                "timestamp": "2024-01-15T08:00:00Z",
                "action": "auto_sync",
                "status": "failed",
                "details": "Rate limit exceeded",
                "error": "Too many requests"
            }
        ]
        
        return APIResponse(
            success=True,
            message="Integration activity retrieved successfully",
            data=activities[:limit]
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch integration activity: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 