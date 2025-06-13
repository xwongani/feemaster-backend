from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime

from ..models import Parent, ParentCreate, ParentUpdate, APIResponse
from ..database import db
from ..auth import get_current_user

router = APIRouter(prefix="/parents", tags=["parents"])

@router.post("", response_model=APIResponse)
async def create_parent(parent: ParentCreate, current_user: dict = Depends(get_current_user)):
    """Create a new parent"""
    try:
        # Check if parent with email already exists
        existing = await db.execute_query(
            "parents",
            "select",
            filters={"email": parent.email},
            select_fields="id"
        )
        
        if existing["success"] and existing["data"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent with this email already exists"
            )
        
        # Create parent record
        result = await db.execute_query(
            "parents",
            "insert",
            data={
                "first_name": parent.first_name,
                "last_name": parent.last_name,
                "email": parent.email,
                "phone": parent.phone,
                "address": parent.address,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create parent"
            )
            
        return APIResponse(
            success=True,
            message="Parent created successfully",
            data={"id": result["data"][0]["id"]}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("", response_model=APIResponse)
async def get_parents(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all parents with optional search"""
    try:
        filters = {}
        if search:
            filters["search"] = search
            
        result = await db.execute_query(
            "parents",
            "select",
            filters=filters,
            select_fields="*",
            limit=limit,
            offset=skip
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch parents"
            )
            
        return APIResponse(
            success=True,
            message="Parents retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{parent_id}", response_model=APIResponse)
async def get_parent(parent_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific parent by ID"""
    try:
        result = await db.execute_query(
            "parents",
            "select",
            filters={"id": parent_id},
            select_fields="*"
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch parent"
            )
            
        if not result["data"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent not found"
            )
            
        return APIResponse(
            success=True,
            message="Parent retrieved successfully",
            data=result["data"][0]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{parent_id}", response_model=APIResponse)
async def update_parent(
    parent_id: str,
    parent: ParentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a parent's information"""
    try:
        # Check if parent exists
        existing = await db.execute_query(
            "parents",
            "select",
            filters={"id": parent_id},
            select_fields="id"
        )
        
        if not existing["success"] or not existing["data"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent not found"
            )
        
        # Update parent
        update_data = parent.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = await db.execute_query(
            "parents",
            "update",
            filters={"id": parent_id},
            data=update_data
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update parent"
            )
            
        return APIResponse(
            success=True,
            message="Parent updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{parent_id}", response_model=APIResponse)
async def delete_parent(parent_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a parent"""
    try:
        # Check if parent exists
        existing = await db.execute_query(
            "parents",
            "select",
            filters={"id": parent_id},
            select_fields="id"
        )
        
        if not existing["success"] or not existing["data"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent not found"
            )
        
        # Delete parent
        result = await db.execute_query(
            "parents",
            "delete",
            filters={"id": parent_id}
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete parent"
            )
            
        return APIResponse(
            success=True,
            message="Parent deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 