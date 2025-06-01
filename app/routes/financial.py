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
        
        return APIResponse(
            success=True,
            message="Financial data export generated successfully",
            data={
                "records": result["data"],
                "total_records": len(result["data"]),
                "export_format": format,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Financial data export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_date_filter_for_period(period: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> str:
    """Helper function to get date filter based on period"""
    if period == "custom" and start_date and end_date:
        return f"AND payment_date BETWEEN '{start_date}' AND '{end_date}'"
    elif period == "current-term":
        # Assuming current term is 4 months
        return "AND payment_date >= CURRENT_DATE - INTERVAL '4 months'"
    elif period == "previous-term":
        return "AND payment_date >= CURRENT_DATE - INTERVAL '8 months' AND payment_date < CURRENT_DATE - INTERVAL '4 months'"
    elif period == "current-year":
        return "AND EXTRACT(YEAR FROM payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:
        return "" 