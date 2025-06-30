import uvicorn
import logging
from fastapi import FastAPI, HTTPException, Depends, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import asyncio
import csv
import io
import os
import time

# Import settings first
from app.config import settings

# Sentry Configuration
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.config import settings

# Initialize Sentry
sentry_sdk.init(
    dsn=settings.sentry_dsn or "https://c5e51e9a2465263c987fe4bed6ab42d9@o4509560859721728.ingest.us.sentry.io/4509560886198272",
    environment=settings.environment,
    integrations=[
        FastApiIntegration(),
        AsyncioIntegration(),
        SqlalchemyIntegration(),
    ],
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    # Enable default PII data collection
    send_default_pii=True,
    # Enable logging
    enable_tracing=True,
)

from app.database import db

from app.routes import auth, students, payments, dashboard, reports, integrations, settings as settings_routes, financial, parents, quickbooks, errors, parent_portal, test_sentry

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
from app.services.cache_service import cache_service
from app.services.integration_service import integration_service
from app.services.quickbooks_service import quickbooks_service
from app.services.twilio_service import twilio_service
from app.services.payment_gateway_service import payment_gateway_service
from app.services.whatsapp_service import whatsapp_service
from app.services.websocket_service import websocket_service
from app.services.audit_service import audit_service
from app.services.bulk_operations_service import bulk_operations_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fee Master Backend API",
    description="Comprehensive school fee management system backend",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["your-domain.com"]
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"}
        )

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
    try:
        # Check database connection
        db_status = await db.check_connection()
        
        # Check service status
        services_status = {
            "analytics": analytics_service.initialized,
            "cache": cache_service.initialized,
            "integration": integration_service.initialized,
            "notification": notification_service.initialized,
            "quickbooks": quickbooks_service.initialized,
            "receipt": receipt_service.initialized,
            "twilio": twilio_service.initialized,
            "payment_gateway": payment_gateway_service.initialized,
            "whatsapp": whatsapp_service.initialized,
            "websocket": websocket_service.initialized,
            "audit": audit_service.initialized,
            "bulk_operations": bulk_operations_service.initialized
        }
        
        return {
            "status": "healthy",
            "database": db_status,
            "services": services_status,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fee Master Backend API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else None
    }

# API info endpoint
@app.get("/api/v1/info")
async def api_info():
    """API information endpoint"""
    return {
        "name": "Fee Master Backend API",
        "version": "2.0.0",
        "description": "Comprehensive school fee management system",
        "features": [
            "Student Management",
            "Fee Management",
            "Payment Processing",
            "Parent Portal",
            "Reporting & Analytics",
            "QuickBooks Integration",
            "Payment Gateway Integration",
            "WhatsApp Integration",
            "Real-time Notifications",
            "Advanced Analytics",
            "Bulk Operations",
            "Audit Trail",
            "WebSocket Support"
        ],
        "integrations": [
            "QuickBooks",
            "Stripe",
            "PayPal",
            "WhatsApp Business API",
            "Twilio SMS"
        ],
        "environment": settings.environment,
        "debug": settings.debug
    }

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(students.router, prefix="/students", tags=["students"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
app.include_router(financial.router, prefix="/financial", tags=["financial"])
app.include_router(parents.router, prefix="/parents", tags=["parents"])
app.include_router(quickbooks.router, prefix="/quickbooks", tags=["quickbooks"])
app.include_router(errors.router, prefix="/errors", tags=["errors"])
app.include_router(parent_portal.router, prefix="/parent-portal", tags=["parent-portal"])
app.include_router(test_sentry.router, prefix="/test-sentry", tags=["test-sentry"])

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
        logger.info("Starting Fee Master Backend...")
        
        # Initialize database
        await db.initialize()
        logger.info("Database initialized")
        
        # Initialize services
        services = [
            analytics_service,
            cache_service,
            integration_service,
            notification_service,
            quickbooks_service,
            receipt_service,
            twilio_service,
            payment_gateway_service,
            whatsapp_service,
            websocket_service,
            audit_service,
            bulk_operations_service
        ]
        
        for service in services:
            try:
                await service.initialize()
                logger.info(f"{service.__class__.__name__} initialized")
            except Exception as e:
                logger.error(f"Failed to initialize {service.__class__.__name__}: {e}")
        
        logger.info("Fee Master Backend started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

# Application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Shutting down Fee Master Backend...")
        
        # Cleanup services
        if hasattr(whatsapp_service, 'cleanup'):
            await whatsapp_service.cleanup()
        
        # Close database connections
        await db.close()
        
        logger.info("Fee Master Backend shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    ) 