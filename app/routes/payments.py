from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from decimal import Decimal
import uuid
from datetime import datetime, date
import logging

from ..models import (
    Payment, PaymentCreate, PaymentPlan, PaymentPlanCreate,
    PaymentReceipt, APIResponse, PaginatedResponse, PaymentStatus
)
from ..database import db
from ..services.receipt_service import receipt_service
from ..services.notification_service import notification_service
from ..services.analytics_service import analytics_service
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/", response_model=APIResponse)
async def create_payment(
    payment: PaymentCreate,
    allocations: Optional[List[dict]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new payment with fee allocations"""
    try:
        # Verify student exists
        student_result = await db.execute_query(
            "students",
            "select",
            filters={"id": payment.student_id},
            select_fields="id, student_id, first_name, last_name"
        )
        
        if not student_result["success"] or not student_result["data"]:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = student_result["data"][0]
        
        # Generate receipt number
        receipt_number = await generate_receipt_number()
        
        # Create payment record
        payment_data = payment.dict()
        payment_data["receipt_number"] = receipt_number
        payment_data["payment_date"] = datetime.utcnow()
        payment_data["payment_status"] = PaymentStatus.completed.value
        
        payment_result = await db.execute_query("payments", "insert", data=payment_data)
        
        if not payment_result["success"]:
            raise HTTPException(status_code=500, detail=payment_result["error"])
        
        created_payment = payment_result["data"][0]
        payment_id = created_payment["id"]
        
        # Handle fee allocations
        total_allocated = 0
        if allocations:
            for allocation in allocations:
                allocation_data = {
                    "payment_id": payment_id,
                    "student_fee_id": allocation["student_fee_id"],
                    "amount": allocation["amount"]
                }
                
                # Create allocation
                allocation_result = await db.execute_query("payment_allocations", "insert", data=allocation_data)
                
                if allocation_result["success"]:
                    total_allocated += float(allocation["amount"])
                    
                    # Update student fee paid status if fully paid
                    fee_check = await db.execute_raw_query("""
                        SELECT 
                            sf.amount,
                            COALESCE(SUM(pa.amount), 0) as total_paid
                        FROM student_fees sf
                        LEFT JOIN payment_allocations pa ON sf.id = pa.student_fee_id
                        WHERE sf.id = $1
                        GROUP BY sf.amount
                    """, [allocation["student_fee_id"]])
                    
                    if fee_check["success"] and fee_check["data"]:
                        fee_data = fee_check["data"][0]
                        if float(fee_data["total_paid"]) >= float(fee_data["amount"]):
                            await db.execute_query(
                                "student_fees",
                                "update",
                                data={"is_paid": True},
                                filters={"id": allocation["student_fee_id"]}
                            )
        
        # Generate and send receipt
        try:
            receipt_data = {
                "payment": created_payment,
                "student": student,
                "allocations": allocations or []
            }
            
            receipt_result = await receipt_service.generate_receipt(
                payment_id, receipt_data, ["email", "download"]
            )
            
            if receipt_result["success"]:
                # Send notifications
                await notification_service.send_payment_confirmation(
                    student["id"], 
                    created_payment,
                    receipt_result["data"]["file_url"]
                )
                
        except Exception as e:
            # Log receipt generation error but don't fail the payment
            await analytics_service.log_activity(
                "receipt_generation_failed",
                f"Failed to generate receipt for payment {payment_id}: {str(e)}",
                current_user["id"],
                {"payment_id": payment_id, "error": str(e)}
            )
        
        # Log payment creation
        await analytics_service.log_activity(
            "payment_created",
            f"Payment of {payment.amount} recorded for {student['first_name']} {student['last_name']}",
            current_user["id"],
            {
                "payment_id": payment_id,
                "student_id": student["student_id"],
                "amount": float(payment.amount),
                "receipt_number": receipt_number
            }
        )
        
        return APIResponse(
            success=True,
            message="Payment created successfully",
            data=created_payment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedResponse)
async def get_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    student_id: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated list of payments with filters"""
    try:
        # Build complex query with joins using materialized view
        payment_view_query = """
            CREATE MATERIALIZED VIEW IF NOT EXISTS payment_details AS
            SELECT 
                p.*,
                s.student_id as student_number,
                s.first_name || ' ' || s.last_name as student_name,
                s.grade,
                pr.receipt_number as receipt_issued,
                pr.file_url as receipt_url,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'fee_type_name', ft.name,
                            'fee_type', ft.fee_type,
                            'allocated_amount', pa.amount
                        )
                    ) FILTER (WHERE pa.id IS NOT NULL), 
                    '[]'
                ) as fee_allocations
            FROM payments p
            JOIN students s ON p.student_id = s.id
            LEFT JOIN payment_receipts pr ON p.id = pr.payment_id
            LEFT JOIN payment_allocations pa ON p.id = pa.payment_id
            LEFT JOIN student_fees sf ON pa.student_fee_id = sf.id
            LEFT JOIN fee_types ft ON sf.fee_type_id = ft.id
            GROUP BY p.id, s.student_id, s.first_name, s.last_name, s.grade, pr.receipt_number, pr.file_url
            WITH DATA;
        """
        
        # Create index on materialized view
        payment_view_index = """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_details_id ON payment_details(id);
            CREATE INDEX IF NOT EXISTS idx_payment_details_date ON payment_details(payment_date);
            CREATE INDEX IF NOT EXISTS idx_payment_details_status ON payment_details(payment_status);
        """
        
        # Execute view creation
        await db.execute_raw_query(payment_view_query)
        await db.execute_raw_query(payment_view_index)
        
        # Build where conditions
        where_conditions = []
        params = []
        param_count = 0
        
        if student_id:
            param_count += 1
            where_conditions.append(f"student_id = ${param_count}")
            params.append(student_id)
            
        if payment_status:
            param_count += 1
            where_conditions.append(f"payment_status = ${param_count}")
            params.append(payment_status)
            
        if payment_method:
            param_count += 1
            where_conditions.append(f"payment_method = ${param_count}")
            params.append(payment_method)
            
        if date_from:
            param_count += 1
            where_conditions.append(f"DATE(payment_date) >= ${param_count}")
            params.append(date_from)
            
        if date_to:
            param_count += 1
            where_conditions.append(f"DATE(payment_date) <= ${param_count}")
            params.append(date_to)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Query using materialized view
        query = f"""
            SELECT * FROM payment_details
            {where_clause}
            ORDER BY payment_date DESC
            LIMIT {per_page} OFFSET {(page - 1) * per_page}
        """
        
        result = await db.execute_raw_query(query, params)
        
        # Get total count using materialized view
        count_query = f"""
            SELECT COUNT(*) FROM payment_details
            {where_clause}
        """
        
        count_result = await db.execute_raw_query(count_query, params)
        total = count_result["data"][0]["count"] if count_result["success"] and count_result["data"] else 0
        
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

@router.get("/{payment_id}", response_model=APIResponse)
async def get_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get payment details with allocations and receipt information"""
    try:
        # Get payment with complete details
        query = """
            SELECT 
                p.*,
                s.student_id as student_number,
                s.first_name || ' ' || s.last_name as student_name,
                s.grade,
                pr.receipt_number,
                pr.file_url as receipt_url,
                pr.sent_via,
                pr.sent_at,
                json_agg(
                    json_build_object(
                        'allocation_id', pa.id,
                        'fee_id', sf.id,
                        'fee_type_name', ft.name,
                        'fee_type', ft.fee_type,
                        'allocated_amount', pa.amount,
                        'due_date', sf.due_date,
                        'academic_year', ay.year_name,
                        'academic_term', at.term_name
                    )
                ) FILTER (WHERE pa.id IS NOT NULL) as allocations
            FROM payments p
            JOIN students s ON p.student_id = s.id
            LEFT JOIN payment_receipts pr ON p.id = pr.payment_id
            LEFT JOIN payment_allocations pa ON p.id = pa.payment_id
            LEFT JOIN student_fees sf ON pa.student_fee_id = sf.id
            LEFT JOIN fee_types ft ON sf.fee_type_id = ft.id
            LEFT JOIN academic_years ay ON sf.academic_year_id = ay.id
            LEFT JOIN academic_terms at ON sf.academic_term_id = at.id
            WHERE p.id = $1
            GROUP BY p.id, s.student_id, s.first_name, s.last_name, s.grade, pr.receipt_number, pr.file_url, pr.sent_via, pr.sent_at
        """
        
        result = await db.execute_raw_query(query, [payment_id])
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        if not result["data"]:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return APIResponse(
            success=True,
            message="Payment retrieved successfully",
            data=result["data"][0]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{payment_id}/status", response_model=APIResponse)
async def update_payment_status(
    payment_id: str,
    status: PaymentStatus,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update payment status"""
    try:
        # Verify payment exists
        existing = await db.execute_query(
            "payments",
            "select",
            filters={"id": payment_id},
            select_fields="id, payment_status, receipt_number"
        )
        
        if not existing["success"] or not existing["data"]:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Update payment status
        update_data = {"payment_status": status.value}
        if notes:
            update_data["notes"] = notes
        
        result = await db.execute_query(
            "payments",
            "update",
            data=update_data,
            filters={"id": payment_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Log status change
        await analytics_service.log_activity(
            "payment_status_updated",
            f"Payment {existing['data'][0]['receipt_number']} status changed to {status.value}",
            current_user["id"],
            {"payment_id": payment_id, "old_status": existing["data"][0]["payment_status"], "new_status": status.value}
        )
        
        return APIResponse(
            success=True,
            message="Payment status updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{payment_id}/receipt", response_model=APIResponse)
async def get_payment_receipt(
    payment_id: str,
    regenerate: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    """Get or regenerate payment receipt"""
    try:
        if regenerate:
            # Get payment data for regeneration
            payment_query = """
                SELECT 
                    p.*,
                    s.student_id as student_number,
                    s.first_name || ' ' || s.last_name as student_name,
                    s.grade
                FROM payments p
                JOIN students s ON p.student_id = s.id
                WHERE p.id = $1
            """
            
            payment_result = await db.execute_raw_query(payment_query, [payment_id])
            
            if not payment_result["success"] or not payment_result["data"]:
                raise HTTPException(status_code=404, detail="Payment not found")
            
            # Regenerate receipt
            receipt_result = await receipt_service.regenerate_receipt(payment_id)
            
            if not receipt_result["success"]:
                raise HTTPException(status_code=500, detail=receipt_result["error"])
            
            return APIResponse(
                success=True,
                message="Receipt regenerated successfully",
                data=receipt_result["data"]
            )
        else:
            # Get existing receipt
            result = await db.execute_query(
                "payment_receipts",
                "select",
                filters={"payment_id": payment_id},
                select_fields="*"
            )
            
            if not result["success"]:
                raise HTTPException(status_code=500, detail=result["error"])
            
            if not result["data"]:
                raise HTTPException(status_code=404, detail="Receipt not found")
            
            return APIResponse(
                success=True,
                message="Receipt retrieved successfully",
                data=result["data"][0]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{payment_id}/receipt/send", response_model=APIResponse)
async def send_payment_receipt(
    payment_id: str,
    channels: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Send payment receipt via specified channels"""
    try:
        # Get payment and receipt data
        query = """
            SELECT 
                p.*,
                s.student_id as student_number,
                s.first_name || ' ' || s.last_name as student_name,
                pr.file_url as receipt_url
            FROM payments p
            JOIN students s ON p.student_id = s.id
            LEFT JOIN payment_receipts pr ON p.id = pr.payment_id
            WHERE p.id = $1
        """
        
        result = await db.execute_raw_query(query, [payment_id])
        
        if not result["success"] or not result["data"]:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        payment_data = result["data"][0]
        
        if not payment_data["receipt_url"]:
            raise HTTPException(status_code=400, detail="No receipt found for this payment")
        
        # Send receipt via specified channels
        send_result = await receipt_service.send_receipt(
            payment_id, 
            payment_data["receipt_url"], 
            channels
        )
        
        if not send_result["success"]:
            raise HTTPException(status_code=500, detail=send_result["error"])
        
        return APIResponse(
            success=True,
            message="Receipt sent successfully",
            data=send_result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/financial", response_model=APIResponse)
async def get_payments_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get financial summary of payments"""
    try:
        date_filter = ""
        params = []
        
        if date_from and date_to:
            date_filter = "AND DATE(payment_date) BETWEEN $1 AND $2"
            params = [date_from, date_to]
        elif date_from:
            date_filter = "AND DATE(payment_date) >= $1"
            params = [date_from]
        elif date_to:
            date_filter = "AND DATE(payment_date) <= $1"
            params = [date_to]
        
        summary_query = f"""
            SELECT 
                COUNT(*) as total_payments,
                COUNT(CASE WHEN payment_status = 'completed' THEN 1 END) as completed_payments,
                COUNT(CASE WHEN payment_status = 'pending' THEN 1 END) as pending_payments,
                COUNT(CASE WHEN payment_status = 'failed' THEN 1 END) as failed_payments,
                COALESCE(SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END), 0) as total_collected,
                COALESCE(SUM(CASE WHEN payment_status = 'pending' THEN amount ELSE 0 END), 0) as total_pending,
                COALESCE(AVG(CASE WHEN payment_status = 'completed' THEN amount END), 0) as average_payment,
                COUNT(DISTINCT student_id) as unique_students
            FROM payments 
            WHERE 1=1 {date_filter}
        """
        
        result = await db.execute_raw_query(summary_query, params)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Get payment methods breakdown
        methods_query = f"""
            SELECT 
                payment_method,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM payments 
            WHERE payment_status = 'completed' {date_filter}
            GROUP BY payment_method
            ORDER BY total_amount DESC
        """
        
        methods_result = await db.execute_raw_query(methods_query, params)
        
        summary_data = result["data"][0] if result["data"] else {}
        summary_data["payment_methods_breakdown"] = methods_result["data"] if methods_result["success"] else []
        
        return APIResponse(
            success=True,
            message="Payment summary retrieved successfully",
            data=summary_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Payment Plans endpoints
@router.post("/plans", response_model=APIResponse)
async def create_payment_plan(
    plan: PaymentPlanCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a payment plan for a student fee"""
    try:
        # Verify student fee exists
        fee_result = await db.execute_query(
            "student_fees",
            "select",
            filters={"id": plan.student_fee_id},
            select_fields="id, amount, is_paid"
        )
        
        if not fee_result["success"] or not fee_result["data"]:
            raise HTTPException(status_code=404, detail="Student fee not found")
        
        fee = fee_result["data"][0]
        
        if fee["is_paid"]:
            raise HTTPException(status_code=400, detail="Fee is already paid")
        
        # Create payment plan
        plan_data = plan.dict()
        plan_result = await db.execute_query("payment_plans", "insert", data=plan_data)
        
        if not plan_result["success"]:
            raise HTTPException(status_code=500, detail=plan_result["error"])
        
        created_plan = plan_result["data"][0]
        plan_id = created_plan["id"]
        
        # Create installments
        installment_amount = plan.total_amount / plan.number_of_installments
        
        for i in range(plan.number_of_installments):
            installment_data = {
                "payment_plan_id": plan_id,
                "installment_number": i + 1,
                "amount": installment_amount,
                "due_date": datetime.utcnow().date()  # You might want to calculate proper due dates
            }
            
            await db.execute_query("payment_plan_installments", "insert", data=installment_data)
        
        return APIResponse(
            success=True,
            message="Payment plan created successfully",
            data=created_plan
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper function
async def generate_receipt_number() -> str:
    """Generate unique receipt number"""
    try:
        # Get the current year and month
        now = datetime.utcnow()
        year_month = now.strftime("%Y%m")
        
        # Get the last receipt number for this month
        query = f"""
            SELECT receipt_number 
            FROM payments 
            WHERE receipt_number LIKE 'RCP{year_month}%'
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        result = await db.execute_raw_query(query)
        
        if result["success"] and result["data"]:
            last_receipt = result["data"][0]["receipt_number"]
            # Extract the sequence number and increment
            sequence = int(last_receipt[-4:]) + 1
        else:
            sequence = 1
        
        return f"RCP{year_month}{sequence:04d}"
        
    except Exception:
        # Fallback to timestamp-based receipt number
        return f"RCP{int(datetime.utcnow().timestamp())}" 