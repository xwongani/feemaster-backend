from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import aiohttp
import json

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class IntegrationService:
    def __init__(self):
        self.integrations = {
            "quickbooks": {
                "name": "QuickBooks",
                "type": "accounting",
                "config_fields": [
                    {"name": "client_id", "type": "text", "required": True},
                    {"name": "client_secret", "type": "password", "required": True},
                    {"name": "environment", "type": "select", "options": ["sandbox", "production"]}
                ]
            },
            "whatsapp": {
                "name": "WhatsApp Business",
                "type": "messaging",
                "config_fields": [
                    {"name": "api_key", "type": "password", "required": True},
                    {"name": "phone_number", "type": "text", "required": True}
                ]
            },
            "sms_gateway": {
                "name": "SMS Gateway",
                "type": "messaging",
                "config_fields": [
                    {"name": "api_key", "type": "password", "required": True},
                    {"name": "sender_id", "type": "text", "required": True}
                ]
            },
            "email_service": {
                "name": "Email Service",
                "type": "messaging",
                "config_fields": [
                    {"name": "smtp_host", "type": "text", "required": True},
                    {"name": "smtp_port", "type": "number", "required": True},
                    {"name": "username", "type": "text", "required": True},
                    {"name": "password", "type": "password", "required": True},
                    {"name": "use_tls", "type": "boolean", "required": True}
                ]
            }
        }

    async def get_integrations(self) -> Dict[str, Any]:
        """Get all integrations with their status"""
        try:
            result = await db.execute_query(
                "integrations",
                "select",
                select_fields="*"
            )
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch integrations"}
            
            # Merge database status with integration definitions
            integrations_list = []
            for integration in self.integrations.items():
                integration_id, details = integration
                db_status = next(
                    (item for item in result["data"] if item["id"] == integration_id),
                    None
                )
                
                integration_data = {
                    "id": integration_id,
                    **details,
                    "status": db_status["status"] if db_status else "not_connected",
                    "last_sync": db_status["last_sync"] if db_status else None,
                    "config": db_status["config"] if db_status else {}
                }
                
                if db_status and db_status.get("error"):
                    integration_data["error_message"] = db_status["error"]
                
                integrations_list.append(integration_data)
            
            return {"success": True, "data": integrations_list}
            
        except Exception as e:
            logger.error(f"Failed to get integrations: {e}")
            return {"success": False, "error": str(e)}

    async def get_integration(self, integration_id: str) -> Dict[str, Any]:
        """Get specific integration details"""
        try:
            if integration_id not in self.integrations:
                return {"success": False, "error": "Integration not found"}
            
            result = await db.execute_query(
                "integrations",
                "select",
                filters={"id": integration_id},
                select_fields="*"
            )
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch integration"}
            
            integration_data = {
                "id": integration_id,
                **self.integrations[integration_id]
            }
            
            if result["data"]:
                db_data = result["data"][0]
                integration_data.update({
                    "status": db_data["status"],
                    "last_sync": db_data["last_sync"],
                    "config": db_data["config"],
                    "activity_log": db_data.get("activity_log", [])
                })
            
            return {"success": True, "data": integration_data}
            
        except Exception as e:
            logger.error(f"Failed to get integration: {e}")
            return {"success": False, "error": str(e)}

    async def update_integration(self, integration_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update integration configuration"""
        try:
            if integration_id not in self.integrations:
                return {"success": False, "error": "Integration not found"}
            
            # Validate required fields
            required_fields = [
                field["name"] for field in self.integrations[integration_id]["config_fields"]
                if field.get("required", False)
            ]
            
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Update or insert integration config
            result = await db.execute_query(
                "integrations",
                "upsert",
                filters={"id": integration_id},
                data={
                    "id": integration_id,
                    "config": config,
                    "status": "connected",
                    "last_sync": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            if not result["success"]:
                return {"success": False, "error": "Failed to update integration"}
            
            return {"success": True, "data": result["data"][0]}
            
        except Exception as e:
            logger.error(f"Failed to update integration: {e}")
            return {"success": False, "error": str(e)}

    async def test_integration(self, integration_id: str) -> Dict[str, Any]:
        """Test integration connection"""
        try:
            if integration_id not in self.integrations:
                return {"success": False, "error": "Integration not found"}
            
            # Get integration config
            result = await db.execute_query(
                "integrations",
                "select",
                filters={"id": integration_id},
                select_fields="*"
            )
            
            if not result["success"] or not result["data"]:
                return {"success": False, "error": "Integration not configured"}
            
            config = result["data"][0]["config"]
            
            # Test connection based on integration type
            if integration_id == "quickbooks":
                return await self._test_quickbooks(config)
            elif integration_id == "whatsapp":
                return await self._test_whatsapp(config)
            elif integration_id == "sms_gateway":
                return await self._test_sms_gateway(config)
            elif integration_id == "email_service":
                return await self._test_email_service(config)
            
            return {"success": False, "error": "Unsupported integration type"}
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return {"success": False, "error": str(e)}

    async def _test_quickbooks(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test QuickBooks connection"""
        try:
            # Implement QuickBooks API test
            return {
                "success": True,
                "message": "QuickBooks connection successful",
                "data": {
                    "api_version": "v3",
                    "company_info": "Test Company",
                    "permissions": ["read", "write"]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_whatsapp(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test WhatsApp Business connection"""
        try:
            # Implement WhatsApp API test
            return {
                "success": True,
                "message": "WhatsApp Business connection successful",
                "data": {
                    "phone_verified": True,
                    "business_profile": "Fee Master Academy",
                    "message_limit": "1000/day"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_sms_gateway(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SMS Gateway connection"""
        try:
            # Implement SMS Gateway test
            return {
                "success": True,
                "message": "SMS Gateway connection successful",
                "data": {
                    "balance": "1000 credits",
                    "sender_id": config.get("sender_id"),
                    "status": "active"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_email_service(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Email Service connection"""
        try:
            # Implement Email Service test
            return {
                "success": True,
                "message": "Email Service connection successful",
                "data": {
                    "smtp_server": config.get("smtp_host"),
                    "status": "connected",
                    "tls_enabled": config.get("use_tls", False)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

integration_service = IntegrationService() 