from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, List

from ..models import APIResponse
from ..services.quickbooks_service import quickbooks_service
# from ..auth import get_current_user  # Comment out the auth import

router = APIRouter(prefix="/quickbooks", tags=["quickbooks"])

# Create a dummy user for testing
async def get_test_user():
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "role": "admin"
    }

@router.get("/auth-url")
async def get_auth_url(current_user: dict = Depends(get_test_user)):  # Use test user instead
    """Get QuickBooks authorization URL"""
    try:
        auth_url = await quickbooks_service.get_auth_url()
        return APIResponse(
            success=True,
            message="QuickBooks authorization URL generated successfully",
            data={"auth_url": auth_url}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/callback")
async def handle_callback(code: str, realm_id: str, current_user: dict = Depends(get_test_user)):  # Use test user instead
    """Handle QuickBooks OAuth callback"""
    try:
        success = await quickbooks_service.handle_callback(code, realm_id)
        if success:
            return APIResponse(
                success=True,
                message="QuickBooks authorization completed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to complete QuickBooks authorization"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/sync-payment")
async def sync_payment(payment_data: Dict, current_user: dict = Depends(get_test_user)):  # Use test user instead
    """Sync payment to QuickBooks"""
    try:
        result = await quickbooks_service.sync_payment(payment_data)
        if result["success"]:
            return APIResponse(
                success=True,
                message="Payment synced to QuickBooks successfully",
                data=result["data"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/accounts")
async def get_accounts(current_user: dict = Depends(get_test_user)):  # Use test user instead
    """Get QuickBooks accounts"""
    try:
        accounts = await quickbooks_service.get_accounts()
        return APIResponse(
            success=True,
            message="QuickBooks accounts retrieved successfully",
            data=accounts
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/payment-methods")
async def get_payment_methods(current_user: dict = Depends(get_test_user)):  # Use test user instead
    """Get QuickBooks payment methods"""
    try:
        payment_methods = await quickbooks_service.get_payment_methods()
        return APIResponse(
            success=True,
            message="QuickBooks payment methods retrieved successfully",
            data=payment_methods
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 