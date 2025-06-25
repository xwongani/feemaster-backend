import logging
import asyncio
import csv
import json
import io
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
from fastapi import UploadFile

from ..config import settings
from ..database import db

logger = logging.getLogger(__name__)

class BulkOperationsService:
    def __init__(self):
        self.initialized = False
        self.max_records = settings.bulk_operation_max_records
        self.timeout = settings.bulk_operation_timeout
        
    async def initialize(self):
        """Initialize bulk operations service"""
        try:
            self.initialized = True
            logger.info("Bulk operations service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bulk operations service: {e}")
    
    async def bulk_import_students(self, file: UploadFile, user_id: str) -> Dict:
        """Bulk import students from CSV/Excel file"""
        try:
            # Validate file
            if not file.filename:
                return {"success": False, "error": "No file provided"}
            
            # Read file content
            content = await file.read()
            
            # Parse based on file type
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(content))
            else:
                return {"success": False, "error": "Unsupported file format. Use CSV or Excel."}
            
            # Validate data
            validation_result = await self._validate_student_data(df)
            if not validation_result["success"]:
                return validation_result
            
            # Process import
            result = await self._process_student_import(df, user_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk import students: {e}")
            return {"success": False, "error": str(e)}
    
    async def bulk_import_payments(self, file: UploadFile, user_id: str) -> Dict:
        """Bulk import payments from CSV/Excel file"""
        try:
            # Validate file
            if not file.filename:
                return {"success": False, "error": "No file provided"}
            
            # Read file content
            content = await file.read()
            
            # Parse based on file type
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(content))
            else:
                return {"success": False, "error": "Unsupported file format. Use CSV or Excel."}
            
            # Validate data
            validation_result = await self._validate_payment_data(df)
            if not validation_result["success"]:
                return validation_result
            
            # Process import
            result = await self._process_payment_import(df, user_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk import payments: {e}")
            return {"success": False, "error": str(e)}
    
    async def bulk_export_students(self, filters: Dict = None, format: str = "csv") -> Dict:
        """Bulk export students to CSV/Excel"""
        try:
            # Get students data
            result = await db.execute_query(
                "students",
                "select",
                filters=filters,
                select_fields="*"
            )
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch students data"}
            
            # Convert to DataFrame
            df = pd.DataFrame(result["data"])
            
            # Export based on format
            if format.lower() == "csv":
                output = io.StringIO()
                df.to_csv(output, index=False)
                content = output.getvalue()
                filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            elif format.lower() == "excel":
                output = io.BytesIO()
                df.to_excel(output, index=False)
                content = output.getvalue()
                filename = f"students_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            else:
                return {"success": False, "error": "Unsupported export format"}
            
            return {
                "success": True,
                "filename": filename,
                "content": content,
                "record_count": len(df),
                "format": format
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk export students: {e}")
            return {"success": False, "error": str(e)}
    
    async def bulk_export_payments(self, filters: Dict = None, format: str = "csv") -> Dict:
        """Bulk export payments to CSV/Excel"""
        try:
            # Get payments data with related information
            query = """
                SELECT 
                    p.id,
                    p.receipt_number,
                    p.amount,
                    p.payment_method,
                    p.payment_status,
                    p.payment_date,
                    p.notes,
                    s.first_name as student_first_name,
                    s.last_name as student_last_name,
                    s.student_id as student_number,
                    s.grade
                FROM payments p
                JOIN students s ON p.student_id = s.id
                ORDER BY p.payment_date DESC
            """
            
            result = await db.execute_raw_query(query)
            
            if not result["success"]:
                return {"success": False, "error": "Failed to fetch payments data"}
            
            # Convert to DataFrame
            df = pd.DataFrame(result["data"])
            
            # Export based on format
            if format.lower() == "csv":
                output = io.StringIO()
                df.to_csv(output, index=False)
                content = output.getvalue()
                filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            elif format.lower() == "excel":
                output = io.BytesIO()
                df.to_excel(output, index=False)
                content = output.getvalue()
                filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            else:
                return {"success": False, "error": "Unsupported export format"}
            
            return {
                "success": True,
                "filename": filename,
                "content": content,
                "record_count": len(df),
                "format": format
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk export payments: {e}")
            return {"success": False, "error": str(e)}
    
    async def bulk_update_students(self, updates: List[Dict], user_id: str) -> Dict:
        """Bulk update students"""
        try:
            if len(updates) > self.max_records:
                return {"success": False, "error": f"Too many records. Maximum allowed: {self.max_records}"}
            
            successful = 0
            failed = 0
            errors = []
            
            for update in updates:
                try:
                    student_id = update.get("id")
                    if not student_id:
                        failed += 1
                        errors.append({"record": update, "error": "Missing student ID"})
                        continue
                    
                    # Remove id from update data
                    update_data = {k: v for k, v in update.items() if k != "id"}
                    
                    result = await db.execute_query(
                        "students",
                        "update",
                        filters={"id": student_id},
                        data=update_data
                    )
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({"record": update, "error": result.get("error", "Update failed")})
                        
                except Exception as e:
                    failed += 1
                    errors.append({"record": update, "error": str(e)})
            
            # Log bulk operation
            await self._log_bulk_operation(
                user_id, "update", "students", len(updates), successful, failed, errors
            )
            
            return {
                "success": True,
                "total": len(updates),
                "successful": successful,
                "failed": failed,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk update students: {e}")
            return {"success": False, "error": str(e)}
    
    async def bulk_delete_students(self, student_ids: List[str], user_id: str) -> Dict:
        """Bulk delete students"""
        try:
            if len(student_ids) > self.max_records:
                return {"success": False, "error": f"Too many records. Maximum allowed: {self.max_records}"}
            
            # Check dependencies
            dependency_check = await self._check_student_dependencies(student_ids)
            if not dependency_check["success"]:
                return dependency_check
            
            successful = 0
            failed = 0
            errors = []
            
            for student_id in student_ids:
                try:
                    result = await db.execute_query(
                        "students",
                        "delete",
                        filters={"id": student_id}
                    )
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({"student_id": student_id, "error": result.get("error", "Delete failed")})
                        
                except Exception as e:
                    failed += 1
                    errors.append({"student_id": student_id, "error": str(e)})
            
            # Log bulk operation
            await self._log_bulk_operation(
                user_id, "delete", "students", len(student_ids), successful, failed, errors
            )
            
            return {
                "success": True,
                "total": len(student_ids),
                "successful": successful,
                "failed": failed,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk delete students: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_student_data(self, df: pd.DataFrame) -> Dict:
        """Validate student data"""
        try:
            required_columns = ["first_name", "last_name", "date_of_birth", "gender", "grade"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Missing required columns: {', '.join(missing_columns)}"
                }
            
            # Check for empty required fields
            for col in required_columns:
                if df[col].isnull().any():
                    return {
                        "success": False,
                        "error": f"Column '{col}' contains empty values"
                    }
            
            # Validate gender values
            valid_genders = ["male", "female", "other"]
            invalid_genders = df[~df["gender"].isin(valid_genders)]["gender"].unique()
            if len(invalid_genders) > 0:
                return {
                    "success": False,
                    "error": f"Invalid gender values: {', '.join(invalid_genders)}"
                }
            
            # Validate date format
            try:
                pd.to_datetime(df["date_of_birth"])
            except:
                return {
                    "success": False,
                    "error": "Invalid date format in date_of_birth column"
                }
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _validate_payment_data(self, df: pd.DataFrame) -> Dict:
        """Validate payment data"""
        try:
            required_columns = ["student_id", "amount", "payment_method", "payment_date"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Missing required columns: {', '.join(missing_columns)}"
                }
            
            # Check for empty required fields
            for col in required_columns:
                if df[col].isnull().any():
                    return {
                        "success": False,
                        "error": f"Column '{col}' contains empty values"
                    }
            
            # Validate payment methods
            valid_methods = ["cash", "credit-card", "mobile-money", "bank-transfer"]
            invalid_methods = df[~df["payment_method"].isin(valid_methods)]["payment_method"].unique()
            if len(invalid_methods) > 0:
                return {
                    "success": False,
                    "error": f"Invalid payment methods: {', '.join(invalid_methods)}"
                }
            
            # Validate amount
            if not pd.to_numeric(df["amount"], errors="coerce").notnull().all():
                return {
                    "success": False,
                    "error": "Invalid amount values"
                }
            
            # Validate date format
            try:
                pd.to_datetime(df["payment_date"])
            except:
                return {
                    "success": False,
                    "error": "Invalid date format in payment_date column"
                }
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _process_student_import(self, df: pd.DataFrame, user_id: str) -> Dict:
        """Process student import"""
        try:
            successful = 0
            failed = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Prepare student data
                    student_data = {
                        "student_id": row.get("student_id", f"STU{datetime.now().strftime('%Y%m%d%H%M%S')}{index}"),
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "date_of_birth": pd.to_datetime(row["date_of_birth"]).date().isoformat(),
                        "gender": row["gender"],
                        "grade": row["grade"],
                        "section": row.get("section"),
                        "status": row.get("status", "active"),
                        "admission_date": pd.to_datetime(row.get("admission_date", datetime.now())).date().isoformat()
                    }
                    
                    result = await db.execute_query(
                        "students",
                        "insert",
                        data=student_data
                    )
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({"row": index + 1, "error": result.get("error", "Insert failed")})
                        
                except Exception as e:
                    failed += 1
                    errors.append({"row": index + 1, "error": str(e)})
            
            # Log bulk operation
            await self._log_bulk_operation(
                user_id, "import", "students", len(df), successful, failed, errors
            )
            
            return {
                "success": True,
                "total": len(df),
                "successful": successful,
                "failed": failed,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to process student import: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_payment_import(self, df: pd.DataFrame, user_id: str) -> Dict:
        """Process payment import"""
        try:
            successful = 0
            failed = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Get student ID
                    student_result = await db.execute_query(
                        "students",
                        "select",
                        filters={"student_id": row["student_id"]},
                        select_fields="id"
                    )
                    
                    if not student_result["success"] or not student_result["data"]:
                        failed += 1
                        errors.append({"row": index + 1, "error": f"Student not found: {row['student_id']}"})
                        continue
                    
                    student_id = student_result["data"][0]["id"]
                    
                    # Prepare payment data
                    payment_data = {
                        "receipt_number": row.get("receipt_number", f"RCP{datetime.now().strftime('%Y%m%d%H%M%S')}{index}"),
                        "student_id": student_id,
                        "amount": float(row["amount"]),
                        "payment_method": row["payment_method"],
                        "payment_status": row.get("payment_status", "completed"),
                        "payment_date": pd.to_datetime(row["payment_date"]).isoformat(),
                        "notes": row.get("notes")
                    }
                    
                    result = await db.execute_query(
                        "payments",
                        "insert",
                        data=payment_data
                    )
                    
                    if result["success"]:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({"row": index + 1, "error": result.get("error", "Insert failed")})
                        
                except Exception as e:
                    failed += 1
                    errors.append({"row": index + 1, "error": str(e)})
            
            # Log bulk operation
            await self._log_bulk_operation(
                user_id, "import", "payments", len(df), successful, failed, errors
            )
            
            return {
                "success": True,
                "total": len(df),
                "successful": successful,
                "failed": failed,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to process payment import: {e}")
            return {"success": False, "error": str(e)}
    
    async def _check_student_dependencies(self, student_ids: List[str]) -> Dict:
        """Check if students have dependencies before deletion"""
        try:
            # Check for payments
            payment_result = await db.execute_query(
                "payments",
                "select",
                filters={"student_id__in": student_ids},
                select_fields="student_id"
            )
            
            if payment_result["success"] and payment_result["data"]:
                students_with_payments = list(set([p["student_id"] for p in payment_result["data"]]))
                return {
                    "success": False,
                    "error": f"Students have payment records: {', '.join(students_with_payments)}"
                }
            
            # Check for student fees
            fee_result = await db.execute_query(
                "student_fees",
                "select",
                filters={"student_id__in": student_ids},
                select_fields="student_id"
            )
            
            if fee_result["success"] and fee_result["data"]:
                students_with_fees = list(set([f["student_id"] for f in fee_result["data"]]))
                return {
                    "success": False,
                    "error": f"Students have fee records: {', '.join(students_with_fees)}"
                }
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _log_bulk_operation(self, user_id: str, operation_type: str, entity_type: str, 
                                total_records: int, successful: int, failed: int, errors: List[Dict]) -> None:
        """Log bulk operation"""
        try:
            log_data = {
                "user_id": user_id,
                "operation_type": operation_type,
                "entity_type": entity_type,
                "total_records": total_records,
                "successful_records": successful,
                "failed_records": failed,
                "errors": json.dumps(errors) if errors else None,
                "status": "completed" if failed == 0 else "completed_with_errors",
                "completed_at": datetime.utcnow()
            }
            
            await db.execute_query(
                "bulk_operation_logs",
                "insert",
                data=log_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log bulk operation: {e}")
    
    async def get_bulk_operation_logs(self, user_id: Optional[str] = None, 
                                    operation_type: Optional[str] = None,
                                    limit: int = 50) -> Dict:
        """Get bulk operation logs"""
        try:
            filters = {}
            if user_id:
                filters["user_id"] = user_id
            if operation_type:
                filters["operation_type"] = operation_type
            
            result = await db.execute_query(
                "bulk_operation_logs",
                "select",
                filters=filters,
                select_fields="*",
                limit=limit,
                order_by="created_at DESC"
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "data": result["data"],
                    "total": len(result["data"])
                }
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Failed to get bulk operation logs: {e}")
            return {"success": False, "error": str(e)}

# Initialize service
bulk_operations_service = BulkOperationsService() 