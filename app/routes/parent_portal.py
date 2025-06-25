from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from ..database import db

router = APIRouter(prefix="/parent-portal", tags=["parent-portal"])

class ParentLookupRequest(BaseModel):
    student_id: Optional[str] = None
    parent_phone: Optional[str] = None

@router.post("/parent-lookup")
async def parent_lookup(payload: ParentLookupRequest):
    if not payload.student_id and not payload.parent_phone:
        raise HTTPException(status_code=400, detail="student_id or parent_phone is required.")

    # Lookup by student_id
    if payload.student_id:
        student_result = await db.execute_query(
            "students",
            "select",
            filters={"student_id": payload.student_id},
            select_fields="*"
        )
        if not student_result["success"] or not student_result["data"]:
            raise HTTPException(status_code=404, detail="Student not found.")
        student = student_result["data"][0]
        # Get parent info
        parent_link_result = await db.execute_query(
            "parent_student_links",
            "select",
            filters={"student_id": student["id"]},
            select_fields="*, parents(*)"
        )
        parents = [pl["parents"] for pl in parent_link_result["data"]] if parent_link_result["success"] and parent_link_result["data"] else []
    # Lookup by parent_phone
    else:
        parent_result = await db.execute_query(
            "parents",
            "select",
            filters={"phone": payload.parent_phone},
            select_fields="*"
        )
        if not parent_result["success"] or not parent_result["data"]:
            raise HTTPException(status_code=404, detail="Parent not found.")
        parent = parent_result["data"][0]
        # Get student links
        link_result = await db.execute_query(
            "parent_student_links",
            "select",
            filters={"parent_id": parent["id"]},
            select_fields="*, students(*)"
        )
        if not link_result["success"] or not link_result["data"]:
            raise HTTPException(status_code=404, detail="No students found for this parent.")
        # For simplicity, return the first student (can be extended to support multiple)
        student = link_result["data"][0]["students"]
        parents = [parent]

    # Get outstanding fees for the student
    fees_result = await db.execute_query(
        "student_fees",
        "select",
        filters={"student_id": student["id"], "is_paid": False},
        select_fields="*"
    )
    outstanding_fees = fees_result["data"] if fees_result["success"] else []

    return {
        "success": True,
        "student": student,
        "parents": parents,
        "outstanding_fees": outstanding_fees
    } 