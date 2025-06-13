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