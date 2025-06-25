from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, date, timedelta
import logging

from ..models import APIResponse
from ..database import db
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/financial", tags=["financial"])

@router.get("/dashboard/overview")
async def get_financial_overview(
    period: str = Query("current-term"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get financial dashboard overview metrics"""
    try:
        # Calculate date range based on period
        date_filter = _get_date_filter_for_period(period, start_date, end_date)
        
        # Get total revenue expected
        revenue_query = f"""
            SELECT 
                COALESCE(SUM(amount), 0) as total_revenue,
                COUNT(*) as total_fee_items
            FROM student_fees
            WHERE 1=1 {date_filter.replace('payment_date', 'created_at')}
        """
        
        # Get collected amount
        collected_query = f"""
            SELECT 
                COALESCE(SUM(amount), 0) as collected,
                COUNT(*) as completed_payments
            FROM payments
            WHERE payment_status = 'completed' {date_filter}
        """
        
        # Get outstanding amount
        outstanding_query = """
            SELECT 
                COALESCE(SUM(sf.amount - COALESCE(sf.paid_amount, 0)), 0) as outstanding
            FROM student_fees sf
            WHERE sf.is_paid = false
        """
        
        revenue_result = await db.execute_raw_query(revenue_query)
        collected_result = await db.execute_raw_query(collected_query)
        outstanding_result = await db.execute_raw_query(outstanding_query)
        
        revenue_data = revenue_result["data"][0] if revenue_result["success"] and revenue_result["data"] else {}
        collected_data = collected_result["data"][0] if collected_result["success"] and collected_result["data"] else {}
        outstanding_data = outstanding_result["data"][0] if outstanding_result["success"] and outstanding_result["data"] else {}
        
        total_revenue = float(revenue_data.get("total_revenue", 0))
        collected = float(collected_data.get("collected", 0))
        outstanding = float(outstanding_data.get("outstanding", 0))
        
        collection_rate = (collected / total_revenue * 100) if total_revenue > 0 else 0
        
        return APIResponse(
            success=True,
            message="Financial overview retrieved successfully",
            data={
                "total_revenue": total_revenue,
                "collected": collected,
                "outstanding": outstanding,
                "collection_rate": round(collection_rate, 1),
                "comparisons": {
                    "total_revenue": 12.5,  # TODO: Calculate actual comparisons
                    "collected": 15.3,
                    "outstanding": 7.2,
                    "collection_rate": 2.8
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Financial overview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/revenue-collections")
async def get_revenue_collections_chart(
    period: str = Query("current-term"),
    current_user: dict = Depends(get_current_user)
):
    """Get revenue vs collections chart data"""
    try:
        # Get monthly data for the last 12 months
        chart_query = """
            WITH monthly_data AS (
                SELECT 
                    TO_CHAR(DATE_TRUNC('month', generate_series), 'Mon') as month,
                    EXTRACT(MONTH FROM generate_series) as month_num,
                    generate_series as month_date
                FROM generate_series(
                    DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months'),
                    DATE_TRUNC('month', CURRENT_DATE),
                    '1 month'::interval
                )
            ),
            revenue_data AS (
                SELECT 
                    DATE_TRUNC('month', created_at) as month_date,
                    SUM(amount) as expected_revenue
                FROM student_fees
                WHERE created_at >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', created_at)
            ),
            collection_data AS (
                SELECT 
                    DATE_TRUNC('month', payment_date) as month_date,
                    SUM(amount) as collected
                FROM payments
                WHERE payment_status = 'completed'
                    AND payment_date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', payment_date)
            )
            SELECT 
                md.month,
                COALESCE(rd.expected_revenue, 0) as expected_revenue,
                COALESCE(cd.collected, 0) as collected
            FROM monthly_data md
            LEFT JOIN revenue_data rd ON md.month_date = rd.month_date
            LEFT JOIN collection_data cd ON md.month_date = cd.month_date
            ORDER BY md.month_num
        """
        
        result = await db.execute_raw_query(chart_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get revenue collections chart")
        
        return APIResponse(
            success=True,
            message="Revenue collections chart data retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Revenue collections chart failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/payment-methods")
async def get_payment_methods_breakdown(
    period: str = Query("current-term"),
    current_user: dict = Depends(get_current_user)
):
    """Get payment methods breakdown for pie chart"""
    try:
        date_filter = _get_date_filter_for_period(period)
        
        methods_query = f"""
            SELECT 
                payment_method,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount,
                ROUND((COUNT(*)::float / (SELECT COUNT(*) FROM payments WHERE payment_status = 'completed' {date_filter}) * 100), 1) as percentage
            FROM payments
            WHERE payment_status = 'completed' {date_filter}
            GROUP BY payment_method
            ORDER BY total_amount DESC
        """
        
        result = await db.execute_raw_query(methods_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get payment methods breakdown")
        
        return APIResponse(
            success=True,
            message="Payment methods breakdown retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Payment methods breakdown failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/monthly-collections")
async def get_monthly_collections_breakdown(
    period: str = Query("current-term"),
    current_user: dict = Depends(get_current_user)
):
    """Get monthly collections breakdown by fee type"""
    try:
        # Get last 6 months of collection data by fee type
        collections_query = """
            SELECT 
                TO_CHAR(p.payment_date, 'Mon') as month,
                EXTRACT(MONTH FROM p.payment_date) as month_num,
                CASE 
                    WHEN p.payment_type = 'tuition' OR p.payment_type = 'Tuition Fee' THEN 'Tuition Fees'
                    WHEN p.payment_type = 'transport' OR p.payment_type = 'Transportation' THEN 'Transport'
                    ELSE 'Other Fees'
                END as fee_category,
                COALESCE(SUM(p.amount), 0) as amount
            FROM payments p
            WHERE p.payment_status = 'completed'
                AND p.payment_date >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY EXTRACT(MONTH FROM p.payment_date), TO_CHAR(p.payment_date, 'Mon'), fee_category
            ORDER BY month_num, fee_category
        """
        
        result = await db.execute_raw_query(collections_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get monthly collections breakdown")
        
        # Transform data for frontend chart
        chart_data = {}
        for row in result["data"]:
            month = row["month"]
            category = row["fee_category"]
            amount = float(row["amount"])
            
            if month not in chart_data:
                chart_data[month] = {"month": month, "month_num": row["month_num"]}
            
            chart_data[month][category.lower().replace(" ", "_")] = amount
        
        # Convert to list and sort by month
        chart_list = sorted(chart_data.values(), key=lambda x: x["month_num"])
        
        return APIResponse(
            success=True,
            message="Monthly collections breakdown retrieved successfully",
            data=chart_list
        )
        
    except Exception as e:
        logger.error(f"Monthly collections breakdown failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/outstanding-by-grade")
async def get_outstanding_by_grade(
    current_user: dict = Depends(get_current_user)
):
    """Get outstanding amounts breakdown by grade"""
    try:
        outstanding_query = """
            SELECT 
                s.grade,
                COUNT(DISTINCT s.id) as total_students,
                COALESCE(SUM(sf.amount - COALESCE(sf.paid_amount, 0)), 0) as outstanding_amount
            FROM students s
            LEFT JOIN student_fees sf ON s.id = sf.student_id AND sf.is_paid = false
            WHERE s.status = 'active'
            GROUP BY s.grade
            ORDER BY s.grade
        """
        
        result = await db.execute_raw_query(outstanding_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get outstanding by grade")
        
        return APIResponse(
            success=True,
            message="Outstanding by grade retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Outstanding by grade failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/recent-transactions")
async def get_recent_transactions(
    limit: int = Query(10, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Get recent financial transactions"""
    try:
        transactions_query = f"""
            SELECT 
                p.id,
                p.receipt_number,
                p.payment_date,
                p.student_name,
                p.amount,
                p.payment_method,
                p.payment_status,
                s.student_id,
                s.grade
            FROM payments p
            LEFT JOIN students s ON p.student_id = s.id
            ORDER BY p.payment_date DESC, p.created_at DESC
            LIMIT {limit}
        """
        
        result = await db.execute_raw_query(transactions_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get recent transactions")
        
        return APIResponse(
            success=True,
            message="Recent transactions retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Recent transactions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/financial-data")
async def export_financial_data(
    format: str = Query("csv", regex="^(csv|excel)$"),
    period: str = Query("current-term"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Export financial data in specified format"""
    try:
        date_filter = _get_date_filter_for_period(period, start_date, end_date)
        
        export_query = f"""
            SELECT 
                p.receipt_number,
                p.payment_date,
                p.student_name,
                s.student_id,
                s.grade,
                p.amount,
                p.payment_method,
                p.payment_status,
                p.payment_type,
                p.notes
            FROM payments p
            LEFT JOIN students s ON p.student_id = s.id
            WHERE 1=1 {date_filter}
            ORDER BY p.payment_date DESC
        """
        
        result = await db.execute_raw_query(export_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to export financial data")
        
        # Convert result to CSV
        import csv
        import io
        output = io.StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerow(["Receipt Number", "Payment Date", "Student Name", "Student ID", "Grade", "Amount", "Payment Method", "Payment Status", "Payment Type", "Notes"])
        for row in result["data"]:
            csv_writer.writerow([row["receipt_number"], row["payment_date"], row["student_name"], row["student_id"], row["grade"], row["amount"], row["payment_method"], row["payment_status"], row["payment_type"], row["notes"]])
        csv_data = output.getvalue()
        
        return APIResponse(
            success=True,
            message="Financial data exported successfully",
            data={"download_url": "data:application/csv;base64," + csv_data}
        )
        
    except Exception as e:
        logger.error(f"Financial data export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_date_filter_for_period(period: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> str:
    """Generate date filter based on period"""
    if start_date and end_date:
        return f"AND payment_date BETWEEN '{start_date}' AND '{end_date}'"
    elif start_date:
        return f"AND payment_date >= '{start_date}'"
    elif end_date:
        return f"AND payment_date <= '{end_date}'"
    
    if period == "current-term":
        return "AND payment_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')"
    elif period == "current-year":
        return "AND payment_date >= DATE_TRUNC('year', CURRENT_DATE)"
    elif period == "last-month":
        return "AND payment_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')"
    elif period == "last-3-months":
        return "AND payment_date >= CURRENT_DATE - INTERVAL '3 months'"
    elif period == "last-6-months":
        return "AND payment_date >= CURRENT_DATE - INTERVAL '6 months'"
    else:
        return ""

# Fee Types CRUD Operations
@router.post("/fee-types", response_model=APIResponse)
async def create_fee_type(
    fee_type_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new fee type"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("fee_types", "insert", data=fee_type_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Fee type created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create fee type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fee-types", response_model=APIResponse)
async def get_fee_types(
    current_user: dict = Depends(get_current_user)
):
    """Get all fee types"""
    try:
        result = await db.execute_query("fee_types", "select", select_fields="*", order_by="name asc")
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Fee types retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fee types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/fee-types/{fee_type_id}", response_model=APIResponse)
async def update_fee_type(
    fee_type_id: str,
    fee_type_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a fee type"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query(
            "fee_types", 
            "update", 
            data=fee_type_data,
            filters={"id": fee_type_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Fee type updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update fee type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/fee-types/{fee_type_id}", response_model=APIResponse)
async def delete_fee_type(
    fee_type_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a fee type"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if fee type is being used
        usage_check = await db.execute_query(
            "student_fees",
            "select",
            filters={"fee_type_id": fee_type_id},
            select_fields="id"
        )
        
        if usage_check["success"] and usage_check["data"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete fee type that is being used by student fees"
            )
        
        result = await db.execute_query("fee_types", "delete", filters={"id": fee_type_id})
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Fee type deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete fee type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Academic Years CRUD Operations
@router.post("/academic-years", response_model=APIResponse)
async def create_academic_year(
    academic_year_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new academic year"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("academic_years", "insert", data=academic_year_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic year created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create academic year: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/academic-years", response_model=APIResponse)
async def get_academic_years(
    current_user: dict = Depends(get_current_user)
):
    """Get all academic years"""
    try:
        result = await db.execute_query("academic_years", "select", select_fields="*", order_by="year_name desc")
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic years retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get academic years: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/academic-years/{academic_year_id}", response_model=APIResponse)
async def update_academic_year(
    academic_year_id: str,
    academic_year_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update an academic year"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query(
            "academic_years", 
            "update", 
            data=academic_year_data,
            filters={"id": academic_year_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic year updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update academic year: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/academic-years/{academic_year_id}", response_model=APIResponse)
async def delete_academic_year(
    academic_year_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an academic year"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if academic year is being used
        usage_check = await db.execute_query(
            "student_fees",
            "select",
            filters={"academic_year_id": academic_year_id},
            select_fields="id"
        )
        
        if usage_check["success"] and usage_check["data"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete academic year that is being used by student fees"
            )
        
        result = await db.execute_query("academic_years", "delete", filters={"id": academic_year_id})
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic year deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete academic year: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Academic Terms CRUD Operations
@router.post("/academic-terms", response_model=APIResponse)
async def create_academic_term(
    academic_term_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new academic term"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query("academic_terms", "insert", data=academic_term_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic term created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create academic term: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/academic-terms", response_model=APIResponse)
async def get_academic_terms(
    academic_year_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all academic terms"""
    try:
        filters = {}
        if academic_year_id:
            filters["academic_year_id"] = academic_year_id
        
        result = await db.execute_query(
            "academic_terms", 
            "select", 
            filters=filters,
            select_fields="*", 
            order_by="term_number asc"
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic terms retrieved successfully",
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get academic terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/academic-terms/{academic_term_id}", response_model=APIResponse)
async def update_academic_term(
    academic_term_id: str,
    academic_term_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update an academic term"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        result = await db.execute_query(
            "academic_terms", 
            "update", 
            data=academic_term_data,
            filters={"id": academic_term_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic term updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update academic term: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/academic-terms/{academic_term_id}", response_model=APIResponse)
async def delete_academic_term(
    academic_term_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an academic term"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if academic term is being used
        usage_check = await db.execute_query(
            "student_fees",
            "select",
            filters={"academic_term_id": academic_term_id},
            select_fields="id"
        )
        
        if usage_check["success"] and usage_check["data"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete academic term that is being used by student fees"
            )
        
        result = await db.execute_query("academic_terms", "delete", filters={"id": academic_term_id})
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Academic term deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete academic term: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Student Fees CRUD Operations
@router.post("/student-fees", response_model=APIResponse)
async def create_student_fee(
    student_fee_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new student fee"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin", "cashier"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        result = await db.execute_query("student_fees", "insert", data=student_fee_data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Student fee created successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create student fee: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/student-fees", response_model=APIResponse)
async def get_student_fees(
    student_id: Optional[str] = None,
    academic_year_id: Optional[str] = None,
    academic_term_id: Optional[str] = None,
    is_paid: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get student fees with filters"""
    try:
        filters = {}
        if student_id:
            filters["student_id"] = student_id
        if academic_year_id:
            filters["academic_year_id"] = academic_year_id
        if academic_term_id:
            filters["academic_term_id"] = academic_term_id
        if is_paid is not None:
            filters["is_paid"] = is_paid
        
        result = await db.execute_query(
            "student_fees", 
            "select", 
            filters=filters,
            select_fields="""
                *,
                students(student_id, first_name, last_name, grade),
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
        logger.error(f"Failed to get student fees: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/student-fees/{student_fee_id}", response_model=APIResponse)
async def update_student_fee(
    student_fee_id: str,
    student_fee_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a student fee"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin", "cashier"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        result = await db.execute_query(
            "student_fees", 
            "update", 
            data=student_fee_data,
            filters={"id": student_fee_id}
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Student fee updated successfully",
            data=result["data"][0] if result["data"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update student fee: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/student-fees/{student_fee_id}", response_model=APIResponse)
async def delete_student_fee(
    student_fee_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a student fee"""
    try:
        # Verify admin permission
        if current_user["role"] not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Check if fee has payments
        payment_check = await db.execute_query(
            "payment_allocations",
            "select",
            filters={"student_fee_id": student_fee_id},
            select_fields="id"
        )
        
        if payment_check["success"] and payment_check["data"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete student fee that has payments"
            )
        
        result = await db.execute_query("student_fees", "delete", filters={"id": student_fee_id})
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return APIResponse(
            success=True,
            message="Student fee deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete student fee: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 