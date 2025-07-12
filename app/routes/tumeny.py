from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.services.tumeny_service import tumeny_service

router = APIRouter()

class PaymentRequest(BaseModel):
    description: str
    parentFirstName: str
    parentLastName: str
    email: Optional[str]
    phoneNumber: str
    amount: int

@router.post("/payment", summary="Create a payment request")

async def create_payment(payment: PaymentRequest):
    try:
        result = await tumeny_service.create_payment(payment.dict())
        return {"success": True, "payment": result.get("payment")}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/payment/{payment_id}", summary="Get payment status")

async def get_payment_status(payment_id: str):
    try:
        result = await tumeny_service.get_payment_status(payment_id)
        return {"success": True, "payment": result.get("payment")}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

class SmsRequest(BaseModel):
    sender: str
    message: str = Field(..., max_length=160)
    recipient: str #comma seperates numbers with country codes


@router.posy("/sms/send", summary="Send SMS via Tumeny")

async def send_sms(sms: SmsRequest):
    try:
        result = await tumeny_service.send_sms(sms.sender, sms.message, sms.recipient)
        return {"success": True, "sms": result.get("sms")}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                                                    
