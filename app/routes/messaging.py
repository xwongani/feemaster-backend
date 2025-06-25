from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import logging

from ..models import APIResponse, MessageCreate, MessageHistory
from ..services.twilio_service import TwilioService
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/messaging", tags=["messaging"])
twilio_service = TwilioService()

@router.post("/send", response_model=APIResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send SMS message to recipients"""
    try:
        if not message_data.recipients:
            raise HTTPException(status_code=400, detail="No recipients specified")

        result = await twilio_service.send_bulk_sms(
            message_data.recipients,
            message_data.message
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to send messages")

        return APIResponse(
            success=True,
            message="Messages sent successfully",
            data=result["results"]
        )

    except Exception as e:
        logger.error(f"Error sending messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=APIResponse)
async def get_message_history(
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """Get message history"""
    try:
        result = await twilio_service.get_message_history(limit)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch message history")

        return APIResponse(
            success=True,
            message="Message history retrieved successfully",
            data=result["messages"]
        )

    except Exception as e:
        logger.error(f"Error fetching message history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recipient-groups", response_model=APIResponse)
async def get_recipient_groups(
    current_user: dict = Depends(get_current_user)
):
    """Get available recipient groups"""
    try:
        result = await twilio_service.get_recipient_groups()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch recipient groups")

        return APIResponse(
            success=True,
            message="Recipient groups retrieved successfully",
            data=result["groups"]
        )

    except Exception as e:
        logger.error(f"Error fetching recipient groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Message Templates CRUD Operations
@router.post("/templates", response_model=APIResponse)
async def create_message_template(
    template_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new message template"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("message_templates", "insert", data=template_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message template created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create message template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates", response_model=APIResponse)
async def get_message_templates(
    template_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all message templates"""
    try:
        filters = {}
        if template_type:
            filters["template_type"] = template_type
        
        result = await db.execute_query(
            "message_templates", 
            "select", 
            filters=filters,
            select_fields="*", 
            order_by="name asc"
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message templates retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/templates/{template_id}", response_model=APIResponse)
async def update_message_template(
    template_id: str,
    template_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a message template"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query(
            "message_templates", 
            "update", 
            data=template_data,
            filters={"id": template_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message template updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update message template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/{template_id}", response_model=APIResponse)
async def delete_message_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message template"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("message_templates", "delete", filters={"id": template_id})
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message template deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete message template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Message Campaigns CRUD Operations
@router.post("/campaigns", response_model=APIResponse)
async def create_message_campaign(
    campaign_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new message campaign"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("message_campaigns", "insert", data=campaign_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message campaign created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create message campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns", response_model=APIResponse)
async def get_message_campaigns(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all message campaigns"""
    try:
        filters = {}
        if status:
            filters["status"] = status
        
        result = await db.execute_query(
            "message_campaigns", 
            "select", 
            filters=filters,
            select_fields="*", 
            order_by="created_at desc"
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message campaigns retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/campaigns/{campaign_id}", response_model=APIResponse)
async def update_message_campaign(
    campaign_id: str,
    campaign_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a message campaign"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query(
            "message_campaigns", 
            "update", 
            data=campaign_data,
            filters={"id": campaign_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message campaign updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update message campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/campaigns/{campaign_id}", response_model=APIResponse)
async def delete_message_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message campaign"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("message_campaigns", "delete", filters={"id": campaign_id})
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Message campaign deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete message campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaigns/{campaign_id}/send", response_model=APIResponse)
async def send_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Send a message campaign"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get campaign details
        campaign_result = await db.execute_query(
            "message_campaigns",
            "select",
            filters={"id": campaign_id},
            select_fields="*"
        )
        
        if not campaign_result["success"] or not campaign_result["data"]:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign = campaign_result["data"][0]
        
        # Update campaign status to sending
        await db.execute_query(
            "message_campaigns",
            "update",
            data={"status": "sending", "sent_at": datetime.utcnow().isoformat()},
            filters={"id": campaign_id}
        )
        
        # Send messages using Twilio service
        result = await twilio_service.send_bulk_sms(
            campaign["recipients"],
            campaign["message"]
        )
        
        if result["success"]:
            # Update campaign status to sent
            await db.execute_query(
                "message_campaigns",
                "update",
                data={"status": "sent", "sent_count": len(result["results"])},
                filters={"id": campaign_id}
            )
        
        return APIResponse(
            success=True,
            message="Campaign sent successfully",
            data=result["results"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 