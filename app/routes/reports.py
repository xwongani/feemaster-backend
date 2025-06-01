from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, date
import csv
import io
import logging

from ..models import ReportRequest, ReportResponse, APIResponse
from ..database import db
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/financial")
async def get_financial_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user)
):
    """Generate financial report"""
    try:
        date_filter = ""
        if date_from and date_to:
            date_filter = f"AND payment_date BETWEEN '{date_from}' AND '{date_to}'"
        elif date_from:
            date_filter = f"AND payment_date >= '{date_from}'"
        elif date_to:
            date_filter = f"AND payment_date <= '{date_to}'"
        
        financial_query = f"""
            SELECT 
                DATE(payment_date) as date,
                payment_method,
                payment_status,
                COUNT(*) as transaction_count,
                COALESCE(SUM(amount), 0) as total_amount,
                COALESCE(AVG(amount), 0) as average_amount
            FROM payments
            WHERE 1=1 {date_filter}
            GROUP BY DATE(payment_date), payment_method, payment_status
            ORDER BY date DESC, payment_method
        """
        
        result = await db.execute_raw_query(financial_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate financial report")
        
        if format == "csv":
            return _generate_csv_response(result["data"], "financial_report.csv")
        
        return APIResponse(
            success=True,
            message="Financial report generated successfully",
            data={
                "report_type": "financial",
                "data": result["data"],
                "total_records": len(result["data"]),
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Financial report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/student")
async def get_student_report(
    grade: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user)
):
    """Generate student report"""
    try:
        where_clauses = []
        if grade:
            where_clauses.append(f"s.current_grade = '{grade}'")
        if status:
            where_clauses.append(f"s.status = '{status}'")
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        student_query = f"""
            SELECT 
                s.student_id,
                s.first_name,
                s.last_name,
                s.current_grade,
                s.current_class,
                s.status,
                s.admission_date,
                s.parent_name,
                s.contact,
                COALESCE(SUM(sf.amount), 0) as total_fees,
                COALESCE(SUM(sf.paid_amount), 0) as total_paid,
                COALESCE(SUM(sf.amount - sf.paid_amount), 0) as outstanding_balance,
                COUNT(sf.id) as fee_items,
                COUNT(CASE WHEN sf.is_paid THEN 1 END) as paid_items,
                CASE 
                    WHEN COUNT(sf.id) = 0 THEN 'no_fees'
                    WHEN COUNT(sf.id) = COUNT(CASE WHEN sf.is_paid THEN 1 END) THEN 'fully_paid'
                    WHEN COUNT(CASE WHEN sf.is_paid THEN 1 END) > 0 THEN 'partially_paid'
                    ELSE 'unpaid'
                END as payment_status
            FROM students s
            LEFT JOIN student_fees sf ON s.id = sf.student_id
            {where_clause}
            GROUP BY s.id, s.student_id, s.first_name, s.last_name, s.current_grade, 
                     s.current_class, s.status, s.admission_date, s.parent_name, s.contact
            ORDER BY s.current_grade, s.last_name, s.first_name
        """
        
        result = await db.execute_raw_query(student_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate student report")
        
        # Filter by payment status if specified
        if payment_status:
            result["data"] = [row for row in result["data"] if row["payment_status"] == payment_status]
        
        if format == "csv":
            return _generate_csv_response(result["data"], "student_report.csv")
        
        return APIResponse(
            success=True,
            message="Student report generated successfully",
            data={
                "report_type": "student",
                "data": result["data"],
                "total_records": len(result["data"]),
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "grade": grade,
                    "status": status,
                    "payment_status": payment_status
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Student report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/class")
async def get_class_report(
    grade: Optional[str] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user)
):
    """Generate class-wise report"""
    try:
        where_clause = f" WHERE current_grade = '{grade}'" if grade else ""
        
        class_query = f"""
            SELECT 
                current_grade,
                current_class,
                COUNT(*) as total_students,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_students,
                COUNT(CASE WHEN gender = 'male' THEN 1 END) as male_students,
                COUNT(CASE WHEN gender = 'female' THEN 1 END) as female_students,
                AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_birth))) as average_age
            FROM students
            {where_clause}
            GROUP BY current_grade, current_class
            ORDER BY current_grade, current_class
        """
        
        result = await db.execute_raw_query(class_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate class report")
        
        if format == "csv":
            return _generate_csv_response(result["data"], "class_report.csv")
        
        return APIResponse(
            success=True,
            message="Class report generated successfully",
            data={
                "report_type": "class",
                "data": result["data"],
                "total_records": len(result["data"]),
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "grade": grade
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Class report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment")
async def get_payment_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    payment_method: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user)
):
    """Generate payment report"""
    try:
        where_clauses = []
        if date_from:
            where_clauses.append(f"payment_date >= '{date_from}'")
        if date_to:
            where_clauses.append(f"payment_date <= '{date_to}'")
        if payment_method:
            where_clauses.append(f"payment_method = '{payment_method}'")
        if status:
            where_clauses.append(f"payment_status = '{status}'")
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        payment_query = f"""
            SELECT 
                p.receipt_number,
                p.payment_date,
                p.student_name,
                s.student_id,
                s.current_grade,
                s.current_class,
                p.amount,
                p.payment_method,
                p.payment_status,
                p.transaction_reference,
                p.notes,
                u.first_name || ' ' || u.last_name as processed_by_name
            FROM payments p
            JOIN students s ON p.student_id = s.id
            LEFT JOIN users u ON p.processed_by = u.id
            {where_clause}
            ORDER BY p.payment_date DESC
        """
        
        result = await db.execute_raw_query(payment_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate payment report")
        
        if format == "csv":
            return _generate_csv_response(result["data"], "payment_report.csv")
        
        return APIResponse(
            success=True,
            message="Payment report generated successfully",
            data={
                "report_type": "payment",
                "data": result["data"],
                "total_records": len(result["data"]),
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None,
                    "payment_method": payment_method,
                    "status": status
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Payment report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/outstanding-fees")
async def get_outstanding_fees_report(
    grade: Optional[str] = Query(None),
    days_overdue: Optional[int] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user)
):
    """Generate outstanding fees report"""
    try:
        where_clauses = ["sf.is_paid = false", "s.status = 'active'"]
        
        if grade:
            where_clauses.append(f"s.current_grade = '{grade}'")
        
        if days_overdue:
            where_clauses.append(f"sf.due_date < CURRENT_DATE - INTERVAL '{days_overdue} days'")
        
        where_clause = " WHERE " + " AND ".join(where_clauses)
        
        outstanding_query = f"""
            SELECT 
                s.student_id,
                s.first_name,
                s.last_name,
                s.current_grade,
                s.current_class,
                s.parent_name,
                s.contact,
                ft.name as fee_type,
                sf.amount,
                sf.paid_amount,
                sf.amount - sf.paid_amount as outstanding_amount,
                sf.due_date,
                CURRENT_DATE - sf.due_date as days_overdue
            FROM student_fees sf
            JOIN students s ON sf.student_id = s.id
            JOIN fee_types ft ON sf.fee_type_id = ft.id
            {where_clause}
            ORDER BY sf.due_date ASC, s.current_grade, s.last_name
        """
        
        result = await db.execute_raw_query(outstanding_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate outstanding fees report")
        
        if format == "csv":
            return _generate_csv_response(result["data"], "outstanding_fees_report.csv")
        
        return APIResponse(
            success=True,
            message="Outstanding fees report generated successfully",
            data={
                "report_type": "outstanding_fees",
                "data": result["data"],
                "total_records": len(result["data"]),
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "grade": grade,
                    "days_overdue": days_overdue
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Outstanding fees report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_reports_summary(current_user: dict = Depends(get_current_user)):
    """Get summary statistics for reports dashboard"""
    try:
        summary_query = """
            SELECT 
                'financial' as report_type,
                COUNT(*) as total_records,
                COALESCE(SUM(amount), 0) as total_amount
            FROM payments
            WHERE payment_date >= CURRENT_DATE - INTERVAL '30 days'
            
            UNION ALL
            
            SELECT 
                'students' as report_type,
                COUNT(*) as total_records,
                0 as total_amount
            FROM students
            WHERE status = 'active'
            
            UNION ALL
            
            SELECT 
                'outstanding' as report_type,
                COUNT(*) as total_records,
                COALESCE(SUM(amount - paid_amount), 0) as total_amount
            FROM student_fees
            WHERE is_paid = false
        """
        
        result = await db.execute_raw_query(summary_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to fetch reports summary")
        
        return APIResponse(
            success=True,
            message="Reports summary retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch reports summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview")
async def get_reports_overview(
    period: str = Query("this-month"),
    current_user: dict = Depends(get_current_user)
):
    """Get overview metrics for reports dashboard"""
    try:
        # Calculate date range based on period
        date_filter = _get_date_filter_for_period(period)
        
        # Get total collections
        collections_query = f"""
            SELECT 
                COALESCE(SUM(amount), 0) as total_collections,
                COUNT(*) as total_transactions
            FROM payments
            WHERE payment_status = 'completed' {date_filter}
        """
        
        collections_result = await db.execute_raw_query(collections_query)
        
        # Get outstanding balance
        outstanding_query = f"""
            SELECT 
                COALESCE(SUM(sf.amount - COALESCE(sf.paid_amount, 0)), 0) as outstanding_balance
            FROM student_fees sf
            WHERE sf.is_paid = false
        """
        
        outstanding_result = await db.execute_raw_query(outstanding_query)
        
        # Calculate collection rate
        total_expected_query = f"""
            SELECT COALESCE(SUM(amount), 0) as total_expected
            FROM student_fees
        """
        
        expected_result = await db.execute_raw_query(total_expected_query)
        
        collections_data = collections_result["data"][0] if collections_result["success"] and collections_result["data"] else {}
        outstanding_data = outstanding_result["data"][0] if outstanding_result["success"] and outstanding_result["data"] else {}
        expected_data = expected_result["data"][0] if expected_result["success"] and expected_result["data"] else {}
        
        total_collections = float(collections_data.get("total_collections", 0))
        outstanding_balance = float(outstanding_data.get("outstanding_balance", 0))
        total_expected = float(expected_data.get("total_expected", 0))
        
        collection_rate = (total_collections / total_expected * 100) if total_expected > 0 else 0
        
        return APIResponse(
            success=True,
            message="Reports overview retrieved successfully",
            data={
                "total_collections": total_collections,
                "outstanding_balance": outstanding_balance,
                "collection_rate": round(collection_rate, 1),
                "total_transactions": int(collections_data.get("total_transactions", 0)),
                "trends": {
                    "collections": 12.5,  # TODO: Calculate actual trends
                    "outstanding": 5.3,
                    "collection_rate": 3.2,
                    "transactions": 8.9
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Reports overview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monthly-collections")
async def get_monthly_collections(
    period: str = Query("this-month"),
    current_user: dict = Depends(get_current_user)
):
    """Get monthly collections data for charts"""
    try:
        # Get last 6 months of data
        monthly_query = """
            SELECT 
                TO_CHAR(payment_date, 'Mon') as month,
                EXTRACT(MONTH FROM payment_date) as month_num,
                SUM(CASE WHEN payment_type = 'tuition' THEN amount ELSE 0 END) as school_fees,
                SUM(CASE WHEN payment_type = 'transport' THEN amount ELSE 0 END) as transport,
                SUM(CASE WHEN payment_type NOT IN ('tuition', 'transport') THEN amount ELSE 0 END) as other_fees
            FROM payments
            WHERE payment_status = 'completed'
                AND payment_date >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY EXTRACT(MONTH FROM payment_date), TO_CHAR(payment_date, 'Mon')
            ORDER BY month_num
        """
        
        result = await db.execute_raw_query(monthly_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get monthly collections")
        
        return APIResponse(
            success=True,
            message="Monthly collections retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Monthly collections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/financial-summary")
async def get_financial_summary(
    period: str = Query("this-month"),
    current_user: dict = Depends(get_current_user)
):
    """Get financial summary by category"""
    try:
        summary_query = """
            SELECT 
                ft.name as category,
                COALESCE(SUM(sf.amount), 0) as expected,
                COALESCE(SUM(CASE WHEN sf.is_paid THEN sf.amount ELSE 0 END), 0) as collected,
                COALESCE(SUM(CASE WHEN NOT sf.is_paid THEN sf.amount ELSE 0 END), 0) as outstanding,
                CASE 
                    WHEN SUM(sf.amount) > 0 THEN 
                        ROUND((SUM(CASE WHEN sf.is_paid THEN sf.amount ELSE 0 END) / SUM(sf.amount) * 100), 1)
                    ELSE 0 
                END as collection_rate
            FROM fee_types ft
            LEFT JOIN student_fees sf ON ft.id = sf.fee_type_id
            GROUP BY ft.id, ft.name
            ORDER BY ft.name
        """
        
        result = await db.execute_raw_query(summary_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get financial summary")
        
        return APIResponse(
            success=True,
            message="Financial summary retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Financial summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/student-reports")
async def get_student_reports(
    period: str = Query("this-month"),
    current_user: dict = Depends(get_current_user)
):
    """Get student reports by grade"""
    try:
        student_reports_query = """
            SELECT 
                s.grade,
                COUNT(*) as total_students,
                COUNT(CASE WHEN payment_summary.payment_status = 'fully_paid' THEN 1 END) as paid_students,
                COUNT(CASE WHEN payment_summary.payment_status != 'fully_paid' THEN 1 END) as unpaid_students,
                CASE 
                    WHEN COUNT(*) > 0 THEN 
                        ROUND((COUNT(CASE WHEN payment_summary.payment_status = 'fully_paid' THEN 1 END)::float / COUNT(*) * 100), 1)
                    ELSE 0 
                END as collection_rate
            FROM students s
            LEFT JOIN (
                SELECT 
                    student_id,
                    CASE 
                        WHEN COUNT(sf.id) = 0 THEN 'no_fees'
                        WHEN COUNT(sf.id) = COUNT(CASE WHEN sf.is_paid THEN 1 END) THEN 'fully_paid'
                        WHEN COUNT(CASE WHEN sf.is_paid THEN 1 END) > 0 THEN 'partially_paid'
                        ELSE 'unpaid'
                    END as payment_status
                FROM student_fees sf
                GROUP BY student_id
            ) payment_summary ON s.id = payment_summary.student_id
            WHERE s.status = 'active'
            GROUP BY s.grade
            ORDER BY s.grade
        """
        
        result = await db.execute_raw_query(student_reports_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get student reports")
        
        return APIResponse(
            success=True,
            message="Student reports retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Student reports failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/class-reports")
async def get_class_reports(
    period: str = Query("this-month"),
    current_user: dict = Depends(get_current_user)
):
    """Get class-wise financial reports"""
    try:
        class_reports_query = """
            SELECT 
                CONCAT(s.grade, s.class_name) as class_name,
                COUNT(*) as students,
                COALESCE(SUM(sf.amount), 0) as total_fees,
                COALESCE(SUM(CASE WHEN sf.is_paid THEN sf.amount ELSE 0 END), 0) as collected,
                COALESCE(SUM(CASE WHEN NOT sf.is_paid THEN sf.amount ELSE 0 END), 0) as outstanding,
                CASE 
                    WHEN SUM(sf.amount) > 0 THEN 
                        ROUND((SUM(CASE WHEN sf.is_paid THEN sf.amount ELSE 0 END) / SUM(sf.amount) * 100), 1)
                    ELSE 0 
                END as collection_rate
            FROM students s
            LEFT JOIN student_fees sf ON s.id = sf.student_id
            WHERE s.status = 'active'
            GROUP BY s.grade, s.class_name
            ORDER BY s.grade, s.class_name
        """
        
        result = await db.execute_raw_query(class_reports_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get class reports")
        
        return APIResponse(
            success=True,
            message="Class reports retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Class reports failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-methods")
async def get_payment_methods_report(
    period: str = Query("this-month"),
    current_user: dict = Depends(get_current_user)
):
    """Get payment methods analysis"""
    try:
        date_filter = _get_date_filter_for_period(period)
        
        payment_methods_query = f"""
            SELECT 
                payment_method as method,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as amount,
                ROUND((COUNT(*)::float / (SELECT COUNT(*) FROM payments WHERE payment_status = 'completed' {date_filter}) * 100), 1) as percentage
            FROM payments
            WHERE payment_status = 'completed' {date_filter}
            GROUP BY payment_method
            ORDER BY amount DESC
        """
        
        result = await db.execute_raw_query(payment_methods_query)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail="Failed to get payment methods report")
        
        return APIResponse(
            success=True,
            message="Payment methods report retrieved successfully",
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Payment methods report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_date_filter_for_period(period: str) -> str:
    """Helper function to get date filter based on period"""
    if period == "this-month":
        return "AND EXTRACT(MONTH FROM payment_date) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif period == "last-month":
        return "AND payment_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND payment_date < DATE_TRUNC('month', CURRENT_DATE)"
    elif period == "this-year":
        return "AND EXTRACT(YEAR FROM payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:
        return ""

def _generate_csv_response(data, filename):
    """Generate CSV response from data"""
    if not data:
        raise HTTPException(status_code=404, detail="No data available for export")
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    response = StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    
    return response 