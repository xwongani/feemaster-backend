from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
import uuid

# Enums
class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"

class PaymentMethod(str, Enum):
    cash = "cash"
    credit_card = "credit-card"
    mobile_money = "mobile-money"
    bank_transfer = "bank-transfer"

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class RelationshipType(str, Enum):
    Father = "Father"
    Mother = "Mother"
    Guardian = "Guardian"
    Other = "Other"

class FeeType(str, Enum):
    tuition = "tuition"
    uniform = "uniform"
    books = "books"
    transport = "transport"
    other = "other"

class UserRole(str, Enum):
    admin = "admin"
    cashier = "cashier"
    teacher = "teacher"
    viewer = "viewer"

class NotificationChannel(str, Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"
    download = "download"

class PaymentPlanStatus(str, Enum):
    active = "active"
    completed = "completed"
    overdue = "overdue"
    cancelled = "cancelled"

class StudentStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    graduated = "graduated"
    transferred = "transferred"

class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"

class AcademicTerm(str, Enum):
    term_1 = "1"
    term_2 = "2" 
    term_3 = "3"

# Base Models
class BaseModelWithID(BaseModel):
    id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Academic Year and Term models
class AcademicYear(BaseModelWithID):
    year_name: str = Field(..., description="Academic year e.g., 2024/2025")
    start_date: date
    end_date: date
    is_current: bool = False
    is_active: bool = True

class AcademicYearCreate(BaseModel):
    year_name: str
    start_date: date
    end_date: date
    is_current: bool = False
    is_active: bool = True

class AcademicTermModel(BaseModelWithID):
    academic_year_id: uuid.UUID
    term_number: AcademicTerm
    term_name: str
    start_date: date
    end_date: date
    is_current: bool = False
    is_active: bool = True

class AcademicTermCreate(BaseModel):
    academic_year_id: uuid.UUID
    term_number: AcademicTerm
    term_name: str
    start_date: date
    end_date: date
    is_current: bool = False
    is_active: bool = True

# School Settings
class SchoolSettings(BaseModel):
    id: Optional[int] = None
    school_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    current_academic_year_id: Optional[uuid.UUID] = None
    current_academic_term_id: Optional[uuid.UUID] = None
    language: str = "en"
    timezone: str = "Africa/Lusaka"
    date_format: str = "DD/MM/YYYY"
    currency: str = "ZMW"
    email_notifications: bool = True
    sms_notifications: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# User Models
class User(BaseModelWithID):
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool = True
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool = True

class UserPermission(BaseModelWithID):
    user_id: uuid.UUID
    permission_name: str
    is_granted: bool = True

# Student Models
class Student(BaseModelWithID):
    student_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    grade: str
    section: Optional[str] = None
    status: StudentStatus = StudentStatus.active
    admission_date: date

class StudentCreate(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    grade: str
    section: Optional[str] = None
    status: StudentStatus = StudentStatus.active
    admission_date: date

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    grade: Optional[str] = None
    section: Optional[str] = None
    status: Optional[StudentStatus] = None

# Parent Models
class Parent(BaseModelWithID):
    first_name: str
    last_name: str
    relationship: RelationshipType
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class ParentCreate(BaseModel):
    first_name: str
    last_name: str
    relationship: RelationshipType
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None

class ParentAccount(BaseModelWithID):
    parent_id: uuid.UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    is_verified: bool = False
    verification_token: Optional[str] = None
    verification_expires_at: Optional[datetime] = None

class ParentStudentLink(BaseModelWithID):
    parent_id: uuid.UUID
    student_id: uuid.UUID
    relationship: RelationshipType
    is_primary_contact: bool = False

class ParentNotificationPreference(BaseModelWithID):
    parent_id: uuid.UUID
    channel: NotificationChannel
    is_enabled: bool = True

# Fee Models
class FeeTypeModel(BaseModelWithID):
    name: str
    description: Optional[str] = None
    fee_type: FeeType
    amount: float
    is_active: bool = True

class FeeTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    fee_type: FeeType
    amount: float
    is_active: bool = True

class StudentFee(BaseModelWithID):
    student_id: uuid.UUID
    fee_type_id: uuid.UUID
    academic_year_id: uuid.UUID
    academic_term_id: uuid.UUID
    amount: float
    due_date: date
    is_paid: bool = False

class StudentFeeCreate(BaseModel):
    student_id: uuid.UUID
    fee_type_id: uuid.UUID
    academic_year_id: uuid.UUID
    academic_term_id: uuid.UUID
    amount: float
    due_date: date

# Payment Models
class Payment(BaseModelWithID):
    receipt_number: str
    student_id: uuid.UUID
    amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus = PaymentStatus.pending
    transaction_reference: Optional[str] = None
    payment_date: datetime
    notes: Optional[str] = None

class PaymentCreate(BaseModel):
    student_id: uuid.UUID
    amount: float
    payment_method: PaymentMethod
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentPlan(BaseModelWithID):
    student_fee_id: uuid.UUID
    total_amount: float
    number_of_installments: int
    status: PaymentPlanStatus = PaymentPlanStatus.active

class PaymentPlanCreate(BaseModel):
    student_fee_id: uuid.UUID
    total_amount: float
    number_of_installments: int

class PaymentPlanInstallment(BaseModelWithID):
    payment_plan_id: uuid.UUID
    installment_number: int
    amount: float
    due_date: date
    is_paid: bool = False
    payment_id: Optional[uuid.UUID] = None

class PaymentAllocation(BaseModelWithID):
    payment_id: uuid.UUID
    student_fee_id: uuid.UUID
    amount: float

class PaymentReceipt(BaseModelWithID):
    payment_id: uuid.UUID
    receipt_number: str
    file_url: Optional[str] = None
    sent_via: Optional[List[NotificationChannel]] = None
    sent_at: Optional[datetime] = None

# Receipt service models
class ReceiptData(BaseModel):
    payment: Dict[str, Any]
    student: Dict[str, Any]
    school_info: Dict[str, Any]

class ReceiptResponse(BaseModel):
    id: str
    payment_id: str
    receipt_number: str
    file_url: str
    created_at: str
    content: Dict[str, Any]

# Class Models
class ClassModel(BaseModelWithID):
    name: str
    grade: str
    section: Optional[str] = None
    academic_year_id: uuid.UUID
    academic_term_id: uuid.UUID
    teacher_id: Optional[uuid.UUID] = None
    capacity: Optional[int] = None
    is_active: bool = True

class ClassCreate(BaseModel):
    name: str
    grade: str
    section: Optional[str] = None
    academic_year_id: uuid.UUID
    academic_term_id: uuid.UUID
    teacher_id: Optional[uuid.UUID] = None
    capacity: Optional[int] = None

class ClassRegister(BaseModelWithID):
    class_id: uuid.UUID
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    academic_term_id: uuid.UUID
    is_enrolled: bool = True
    enrollment_date: date

class AttendanceRecord(BaseModelWithID):
    class_register_id: uuid.UUID
    date: date
    status: AttendanceStatus
    notes: Optional[str] = None
    recorded_by: Optional[uuid.UUID] = None

# Integration Models
class IntegrationSettings(BaseModelWithID):
    integration_name: str
    is_enabled: bool = False
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None

class IntegrationLog(BaseModelWithID):
    integration_name: str
    action: str
    status: str
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class QuickBooksSyncLog(BaseModelWithID):
    entity_type: str
    entity_id: uuid.UUID
    quickbooks_id: Optional[str] = None
    sync_status: str
    error_message: Optional[str] = None

# Report Models
class ReportTemplate(BaseModelWithID):
    name: str
    description: Optional[str] = None
    template_type: str
    parameters: Optional[Dict[str, Any]] = None
    created_by: Optional[uuid.UUID] = None
    is_public: bool = False

class SavedReport(BaseModelWithID):
    template_id: Optional[uuid.UUID] = None
    name: str
    parameters: Optional[Dict[str, Any]] = None
    file_url: Optional[str] = None
    generated_by: Optional[uuid.UUID] = None

# Bulk import models
class BulkImport(BaseModelWithID):
    import_type: str
    file_name: str
    status: str
    total_records: Optional[int] = None
    processed_records: Optional[int] = None
    failed_records: Optional[int] = None
    error_log: Optional[str] = None
    imported_by: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None

# Reminder models
class PaymentReminder(BaseModelWithID):
    student_fee_id: uuid.UUID
    reminder_type: str
    due_date: date
    status: str
    sent_via: Optional[List[NotificationChannel]] = None
    sent_at: Optional[datetime] = None
    message: Optional[str] = None

# Backup models
class BackupLog(BaseModelWithID):
    backup_type: str
    status: str
    file_url: Optional[str] = None
    size_bytes: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

# Audit models
class AuditLog(BaseModelWithID):
    user_id: Optional[uuid.UUID] = None
    action: str
    table_name: str
    record_id: uuid.UUID
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None

# Response models
class DashboardStats(BaseModel):
    total_students: int
    total_collections: float
    pending_payments: float
    receipts_generated: int
    collection_rate: float
    recent_activities: List[Dict[str, Any]]
    current_academic_year: str
    current_academic_term: str

class FinancialSummary(BaseModel):
    total_revenue: float
    collected: float
    outstanding: float
    collection_rate: float
    trends: Dict[str, float]

class PaymentSummary(BaseModel):
    student_id: str
    student_name: str
    grade: str
    total_fees: float
    total_paid: float
    outstanding: float
    payment_status: str

# Authentication models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

# Alias for backward compatibility
UserLogin = LoginRequest

# API Response models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

class PaginatedResponse(BaseModel):
    success: bool
    data: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int

# File upload models
class FileUpload(BaseModel):
    filename: str
    content_type: str
    bucket: str
    file_path: str
    size: int

# Notification models
class NotificationCreate(BaseModel):
    recipient_type: str
    recipient_id: str
    channel: NotificationChannel
    message: str
    subject: Optional[str] = None

# Settings models
class SystemSettings(BaseModel):
    school_name: str
    school_email: Optional[str] = None
    school_phone: Optional[str] = None
    school_address: Optional[str] = None
    academic_year: str
    current_term: str
    currency: str = "ZMW"
    timezone: str = "Africa/Lusaka"
    date_format: str = "DD/MM/YYYY"
    time_format: str = "24h"
    language: str = "en"

class PaymentSettings(BaseModel):
    accept_cash: bool = True
    accept_bank_transfer: bool = True
    accept_mobile_money: bool = True
    accept_credit_card: bool = False
    accept_debit_card: bool = True
    accept_cheque: bool = False
    late_fee_percentage: float = 5.0
    grace_period_days: int = 7
    auto_reminders: bool = True
    reminder_frequency: str = "weekly"
    payment_confirmation: bool = True
    receipt_generation: bool = True

class NotificationSettings(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = True
    whatsapp_notifications: bool = True
    push_notifications: bool = False
    payment_confirmations: bool = True
    payment_reminders: bool = True
    overdue_notifications: bool = True
    receipt_delivery: bool = True
    system_alerts: bool = True
    maintenance_notifications: bool = True

# Report models
class ReportRequest(BaseModel):
    report_type: str
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    filters: Optional[Dict[str, Any]] = None
    format: str = "json"

class ReportResponse(BaseModel):
    report_type: str
    data: List[Dict[str, Any]]
    total_records: int
    generated_at: str
    filters_applied: Optional[Dict[str, Any]] = None

# Integration models
class Integration(BaseModel):
    id: str
    name: str
    type: str
    status: str
    description: str
    last_sync: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None

class IntegrationConfig(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    api_key: Optional[str] = None
    phone_number: Optional[str] = None
    environment: Optional[str] = None
    sender_id: Optional[str] = None

# Response models for API endpoints
class PaymentResponse(BaseModel):
    id: uuid.UUID
    receipt_number: str
    student_id: uuid.UUID
    amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    payment_date: datetime
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus
    notes: Optional[str] = None

class StudentResponse(BaseModel):
    id: uuid.UUID
    student_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    grade: str
    section: Optional[str] = None
    status: StudentStatus
    admission_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None

class StudentFeeResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    fee_type_id: uuid.UUID
    academic_year_id: uuid.UUID
    academic_term_id: uuid.UUID
    amount: float
    due_date: date
    is_paid: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class ParentResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    relationship: RelationshipType
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class PaymentPlanResponse(BaseModel):
    id: uuid.UUID
    student_fee_id: uuid.UUID
    total_amount: float
    number_of_installments: int
    status: PaymentPlanStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

class BulkPaymentResponse(BaseModel):
    total_processed: int
    successful_payments: int
    failed_payments: int
    total_amount: float
    payment_ids: List[uuid.UUID]
    errors: Optional[List[str]] = None

class QuickBooksExportResponse(BaseModel):
    export_id: str
    status: str
    records_exported: int
    export_date: datetime
    file_url: Optional[str] = None 