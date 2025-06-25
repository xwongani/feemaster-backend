import uvicorn
import logging
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import asyncio
import csv
import io
import os

from app.config import settings
from app.database import db

# Import all route modules
from app.routes import auth, students, payments, dashboard, reports, integrations, settings as settings_routes, financial, parents, quickbooks, errors
from app.routes import parent_portal

# Import models
from app.models import (
    PaymentCreate, PaymentResponse, PaymentStatusUpdate,
    StudentCreate, StudentResponse, StudentFeeResponse,
    ParentCreate, ParentResponse,
    ReceiptResponse, NotificationCreate, NotificationChannel,
    PaymentPlanCreate, PaymentPlanResponse,
    BulkPaymentResponse, QuickBooksExportResponse,
    DashboardStats, APIResponse
)

# Import services
from app.services.notification_service import notification_service
from app.services.receipt_service import receipt_service
from app.services.analytics_service import analytics_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fee Master - School Administration System",
    description="Comprehensive school fee management system with payment processing, student management, financial reporting, and integrations",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security
security = HTTPBearer()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(auth.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(settings_routes.router, prefix="/api/v1")
app.include_router(financial.router, prefix="/api/v1")
app.include_router(parents.router, prefix="/api/v1")
app.include_router(quickbooks.router, prefix="/api/v1")
app.include_router(errors.router, prefix="/api/v1")
app.include_router(parent_portal.router, prefix="/api/v1")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify authentication and return current user"""
    try:
        # Import get_current_user from auth routes
        from app.routes.auth import get_current_user as auth_get_current_user
        return await auth_get_current_user(credentials)
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0",
        "service": "Fee Master Backend"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Fee Master API",
        "version": "2.1.0",
        "docs": "/docs",
        "health": "/health"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

# Application startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize database
        await db.connect()
        
        # Initialize notification service
        await notification_service.initialize()
        
        # Start overdue reminders scheduler
        asyncio.create_task(notification_service.schedule_overdue_reminders())
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# Application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    try:
        # Cleanup notification service
        await notification_service.cleanup()
        
        # Close database connections
        await db.disconnect()
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Shutdown failed: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    ) 