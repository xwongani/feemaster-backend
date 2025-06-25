from fastapi import APIRouter, HTTPException
import sentry_sdk
import logging

router = APIRouter(prefix="/test-sentry", tags=["test-sentry"])

@router.get("/error")
async def test_error():
    """Test error tracking in Sentry"""
    try:
        # Simulate an error
        raise ValueError("This is a test error from the backend!")
    except Exception as e:
        # Capture the exception in Sentry
        sentry_sdk.capture_exception(e)
        logging.error(f"Test error captured: {str(e)}")
        raise HTTPException(status_code=500, detail="Test error triggered")

@router.get("/tracing")
async def test_tracing():
    """Test performance tracing in Sentry"""
    with sentry_sdk.start_span(op="test", description="Backend API Call") as span:
        span.set_tag("test_type", "tracing")
        span.set_data("custom_data", "test_value")
        
        # Simulate some work
        import asyncio
        await asyncio.sleep(0.1)
        
        logging.info("Tracing test completed")
        return {"message": "Tracing test completed", "span_id": span.span_id}

@router.get("/log")
async def test_logging():
    """Test logging to Sentry"""
    logging.info("This is an info log from the backend")
    logging.warning("This is a warning log from the backend")
    logging.error("This is an error log from the backend")
    
    return {"message": "Logging test completed"} 