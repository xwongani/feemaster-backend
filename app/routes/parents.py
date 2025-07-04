from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Header
from typing import List, Optional
from datetime import datetime
import csv
from io import StringIO
import os

from ..models import Parent, ParentCreate, ParentUpdate, APIResponse
from ..database import db
from ..auth import get_current_user

router = APIRouter(prefix="/parents", tags=["parents"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "your-very-secret-key")

async def verify_admin_api_key(x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

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

@router.post("/bulk-import", response_model=APIResponse)
async def bulk_import_parents(
    file: UploadFile = File(...),
    admin_auth: None = Depends(verify_admin_api_key),
    current_user: dict = Depends(get_current_user)
):
    """Bulk import parents from CSV file"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be CSV format")
        content = await file.read()
        csv_content = content.decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_content))
        successful_imports = 0
        failed_imports = 0
        errors = []
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                parent_data = {
                    "first_name": row.get("first_name", "").strip(),
                    "last_name": row.get("last_name", "").strip(),
                    "relationship": row.get("relationship", "").strip(),
                    "phone": row.get("phone", "").strip() or None,
                    "email": row.get("email", "").strip() or None,
                    "emergency_contact": row.get("emergency_contact", "false").strip().lower() == "true"
                }
                if not all([parent_data["first_name"], parent_data["last_name"], parent_data["relationship"]]) or (not parent_data["phone"] and not parent_data["email"]):
                    errors.append(f"Row {row_num}: Missing required fields")
                    failed_imports += 1
                    continue
                # Check if parent already exists (by phone or email)
                filters = {}
                if parent_data["phone"]:
                    filters["phone"] = parent_data["phone"]
                if parent_data["email"]:
                    filters["email"] = parent_data["email"]
                existing = await db.execute_query("parents", "select", filters=filters, select_fields="id")
                if existing["success"] and existing["data"]:
                    errors.append(f"Row {row_num}: Parent already exists")
                    failed_imports += 1
                    continue
                result = await db.execute_query("parents", "insert", data=parent_data)
                if result["success"]:
                    successful_imports += 1
                else:
                    errors.append(f"Row {row_num}: {result['error']}")
                    failed_imports += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                failed_imports += 1
        return APIResponse(
            success=True,
            message=f"Import completed: {successful_imports} successful, {failed_imports} failed",
            data={
                "successful_imports": successful_imports,
                "failed_imports": failed_imports,
                "errors": errors
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 