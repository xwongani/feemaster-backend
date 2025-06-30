from fastapi import APIRouter, HTTPException, Depends, Query, status, UploadFile, File, Body
from typing import List, Optional
import uuid
import csv
from io import StringIO

from ..database import db
from ..models import (
    Student, StudentCreate, StudentUpdate, APIResponse, PaginatedResponse
)
from ..services.analytics_service import analytics_service
from ..auth import get_current_user

router = APIRouter(prefix="/students", tags=["students"])

@router.get("/", response_model=PaginatedResponse)
async def get_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    grade: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated list of students with search and filters"""
    try:
        filters = {}
        
        # Add filters based on query parameters
        if grade:
            filters["grade"] = grade
        if status:
            filters["status"] = status
        if search:
            # Optimized search query with parameterized values
            search_query = """
                WITH student_data AS (
                    SELECT 
                        s.*,
                        psl.relationship,
                        p.first_name as parent_first_name,
                        p.last_name as parent_last_name,
                        p.phone as parent_phone
                    FROM students s
                    LEFT JOIN parent_student_links psl ON s.id = psl.student_id AND psl.is_primary_contact = true
                    LEFT JOIN parents p ON psl.parent_id = p.id
                    WHERE (
                        s.first_name ILIKE $1 
                        OR s.last_name ILIKE $1 
                        OR s.student_id ILIKE $1
                    )
                    {grade_filter}
                    {status_filter}
                )
                SELECT * FROM student_data
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """.format(
                grade_filter=f"AND s.grade = ${param_count + 1}" if grade else "",
                status_filter=f"AND s.status = ${param_count + 2}" if status else ""
            )
            
            # Prepare parameters
            search_param = f"%{search}%"
            params = [search_param]
            if grade:
                params.append(grade)
            if status:
                params.append(status)
            params.extend([per_page, (page - 1) * per_page])
            
            result = await db.execute_raw_query(search_query, params)
            
            # Optimized count query
            count_query = """
                SELECT COUNT(*)
                FROM students s
                WHERE (
                    s.first_name ILIKE $1 
                    OR s.last_name ILIKE $1 
                    OR s.student_id ILIKE $1
                )
                {grade_filter}
                {status_filter}
            """.format(
                grade_filter=f"AND s.grade = ${param_count + 1}" if grade else "",
                status_filter=f"AND s.status = ${param_count + 2}" if status else ""
            )
            
            count_result = await db.execute_raw_query(count_query, params[:-2])  # Exclude pagination params
            total = count_result["data"][0]["count"] if count_result["success"] and count_result["data"] else 0
        else:
            # Simple query without complex joins for testing
            result = await db.execute_query(
                "students",
                "select",
                filters=filters,
                select_fields="*",
                limit=per_page,
                offset=(page - 1) * per_page
            )
            
            # Get total count
            count_result = await db.execute_query("students", "select", filters=filters, select_fields="*")
            total = len(count_result["data"]) if count_result["success"] else 0
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        total_pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            success=True,
            data=result["data"],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{student_id}", response_model=APIResponse)
async def get_student(
    student_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get student by ID with complete profile information"""
    try:
        # Get student with parent information
        result = await db.execute_query(
            "students",
            "select",
            filters={"id": student_id},
            select_fields="""
                *,
                parent_student_links(
                    relationship,
                    is_primary_contact,
                    parents(*)
                )
            """
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        if not result["data"]:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = result["data"][0]
        
        # Get academic context
        academic_context = await db.get_current_academic_context()
        
        # Get student fees for current academic year
        if academic_context["success"] and academic_context["data"]["academic_year"]:
            fees_result = await db.execute_query(
                "student_fees",
                "select",
                filters={
                    "student_id": student_id,
                    "academic_year_id": academic_context["data"]["academic_year"]["id"]
                },
                select_fields="""
                    *,
                    fee_types(name, fee_type, description),
                    academic_years(year_name),
                    academic_terms(term_name)
                """
            )
            student["fees"] = fees_result["data"] if fees_result["success"] else []
        
        # Get payment history
        payments_result = await db.execute_query(
            "payments",
            "select",
            filters={"student_id": student_id},
            select_fields="*",
            order_by="payment_date desc",
            limit=10
        )
        student["recent_payments"] = payments_result["data"] if payments_result["success"] else []
        
        return APIResponse(
            success=True,
            message="Student retrieved successfully",
            data=student
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=APIResponse)
async def create_student(
    student: StudentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new student"""
    try:
        # Check if student ID already exists
        existing = await db.execute_query(
            "students",
            "select",
            filters={"student_id": student.student_id},
            select_fields="id"
        )
        
        if existing["success"] and existing["data"]:
            raise HTTPException(status_code=400, detail="Student ID already exists")
        
        # Create student record
        student_data = student.dict()
        result = await db.execute_query("students", "insert", data=student_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Log the action
        await analytics_service.log_activity(
            "student_created",
            f"New student {student.first_name} {student.last_name} added",
            current_user["id"],
            {"student_id": student.student_id}
        )
        
        return APIResponse(
            success=True,
            message="Student created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{student_id}", response_model=APIResponse)
async def update_student(
    student_id: str,
    student_update: StudentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update student information"""
    try:
        # Check if student exists
        existing = await db.execute_query(
            "students",
            "select",
            filters={"id": student_id},
            select_fields="id, first_name, last_name"
        )
        
        if not existing["success"] or not existing["data"]:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Update student record
        update_data = {k: v for k, v in student_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        result = await db.execute_query(
            "students",
            "update",
            data=update_data,
            filters={"id": student_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Log the action
        await analytics_service.log_activity(
            "student_updated",
            f"Student {existing['data'][0]['first_name']} {existing['data'][0]['last_name']} updated",
            current_user["id"],
            {"student_id": student_id, "updates": update_data}
        )
        
        return APIResponse(
            success=True,
            message="Student updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{student_id}", response_model=APIResponse)
async def delete_student(
    student_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a student (soft delete by changing status)"""
    try:
        # Check if student exists
        existing = await db.execute_query(
            "students",
            "select",
            filters={"id": student_id},
            select_fields="id, first_name, last_name, status"
        )
        
        if not existing["success"] or not existing["data"]:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Check if student has any pending payments
        pending_payments = await db.execute_query(
            "student_fees",
            "select",
            filters={"student_id": student_id, "is_paid": False},
            select_fields="id"
        )
        
        if pending_payments["success"] and pending_payments["data"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete student with pending fee payments"
            )
        
        # Soft delete by updating status
        result = await db.execute_query(
            "students",
            "update",
            data={"status": "inactive"},
            filters={"id": student_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Log the action
        await analytics_service.log_activity(
            "student_deleted",
            f"Student {existing['data'][0]['first_name']} {existing['data'][0]['last_name']} deactivated",
            current_user["id"],
            {"student_id": student_id}
        )
        
        return APIResponse(
            success=True,
            message="Student deactivated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{student_id}/fees", response_model=APIResponse)
async def get_student_fees(
    student_id: str,
    academic_year_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get all fees for a student"""
    try:
        filters = {"student_id": student_id}
        
        if academic_year_id:
            filters["academic_year_id"] = academic_year_id
        else:
            # Get current academic year
            academic_context = await db.get_current_academic_context()
            if academic_context["success"] and academic_context["data"]["academic_year"]:
                filters["academic_year_id"] = academic_context["data"]["academic_year"]["id"]
        
        result = await db.execute_query(
            "student_fees",
            "select",
            filters=filters,
            select_fields="""
                *,
                fee_types(name, fee_type, description),
                academic_years(year_name),
                academic_terms(term_name)
            """,
            order_by="due_date asc"
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Student fees retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{student_id}/payments", response_model=APIResponse)
async def get_student_payments(
    student_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all payments for a student"""
    try:
        result = await db.execute_raw_query("""
            SELECT 
                p.*,
                array_agg(
                    json_build_object(
                        'fee_type_name', ft.name,
                        'fee_type', ft.fee_type,
                        'amount', pa.amount
                    )
                ) as allocated_fees
            FROM payments p
            LEFT JOIN payment_allocations pa ON p.id = pa.payment_id
            LEFT JOIN student_fees sf ON pa.student_fee_id = sf.id
            LEFT JOIN fee_types ft ON sf.fee_type_id = ft.id
            WHERE p.student_id = $1
            GROUP BY p.id
            ORDER BY p.payment_date DESC
        """, [student_id])
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Student payments retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-import", response_model=APIResponse)
async def bulk_import_students(
    file: UploadFile = File(...)
):
    """Bulk import students from CSV file"""
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
                # Map CSV columns to student model
                student_data = {
                    "student_id": row.get("student_id", "").strip(),
                    "first_name": row.get("first_name", "").strip(),
                    "middle_name": row.get("middle_name", "").strip() or None,
                    "last_name": row.get("last_name", "").strip(),
                    "date_of_birth": row.get("date_of_birth", "").strip(),
                    "gender": row.get("gender", "").strip().lower(),
                    "grade": row.get("grade", "").strip(),
                    "section": row.get("section", "").strip() or None,
                    "admission_date": row.get("admission_date", "").strip()
                }
                
                # Validate required fields
                if not all([student_data["student_id"], student_data["first_name"], 
                           student_data["last_name"], student_data["grade"]]):
                    errors.append(f"Row {row_num}: Missing required fields")
                    failed_imports += 1
                    continue
                
                # Check if student already exists
                existing = await db.execute_query(
                    "students",
                    "select",
                    filters={"student_id": student_data["student_id"]},
                    select_fields="id"
                )
                
                if existing["success"] and existing["data"]:
                    errors.append(f"Row {row_num}: Student ID {student_data['student_id']} already exists")
                    failed_imports += 1
                    continue
                
                # Create student
                result = await db.execute_query("students", "insert", data=student_data)
                
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

@router.get("/stats/overview", response_model=APIResponse)
async def get_students_overview(
    # current_user: dict = Depends(get_current_user)  # Temporarily disabled for development
):
    """Get students overview statistics"""
    try:
        # Get all students
        all_students = await db.execute_query(
            "students",
            "select",
            select_fields="*"
        )
        
        if not all_students["success"]:
            raise HTTPException(status_code=500, detail=all_students["error"])
        
        students_data = all_students["data"]
        
        # Calculate stats
        total_students = len(students_data)
        active_students = len([s for s in students_data if s.get("status") == "active"])
        inactive_students = total_students - active_students
        
        # For payment stats, we'll use placeholder values for now
        # These would normally come from payment/fee tables
        fully_paid = 2
        partially_paid = 2
        unpaid = 1
        
        return APIResponse(
            success=True,
            message="Students overview retrieved successfully",
            data={
                "total_students": total_students,
                "active_students": active_students,
                "inactive_students": inactive_students,
                "fully_paid": fully_paid,
                "partially_paid": partially_paid,
                "unpaid": unpaid
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/student-lookup", response_model=APIResponse)
async def student_lookup(
    payload: dict = Body(..., example={
        "student_id": "STU12345",
        "parent_phone": "0712345678",
        "parent_id": "parent-uuid"
    }),
    current_user: dict = Depends(get_current_user)
):
    """Advanced student lookup by student_id, parent_phone, or parent_id."""
    try:
        student_id = payload.get("student_id")
        parent_phone = payload.get("parent_phone")
        parent_id = payload.get("parent_id")
        
        if not (student_id or parent_phone or parent_id):
            return APIResponse(success=False, message="Provide at least one of student_id, parent_phone, or parent_id.", data=None)
        
        # Build query
        if student_id:
            result = await db.execute_query(
                "students",
                "select",
                filters={"student_id": student_id},
                select_fields="*"
            )
            students = result["data"] if result["success"] else []
        elif parent_id:
            # Find all students linked to this parent
            query = """
                SELECT s.* FROM students s
                JOIN parent_student_links psl ON s.id = psl.student_id
                WHERE psl.parent_id = $1
            """
            result = await db.execute_raw_query(query, [parent_id])
            students = result["data"] if result["success"] else []
        elif parent_phone:
            # Find all students linked to this parent phone
            query = """
                SELECT s.* FROM students s
                JOIN parent_student_links psl ON s.id = psl.student_id
                JOIN parents p ON psl.parent_id = p.id
                WHERE p.phone = $1
            """
            result = await db.execute_raw_query(query, [parent_phone])
            students = result["data"] if result["success"] else []
        else:
            students = []
        
        return APIResponse(
            success=True,
            message="Student(s) found" if students else "No students found",
            data=students
        )
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None) 