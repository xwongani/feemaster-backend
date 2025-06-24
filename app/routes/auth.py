from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
import jwt
import bcrypt
import logging

from ..models import UserLogin, UserCreate, Token, User, APIResponse
from ..database import db
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Test user credentials (for development only)
TEST_USER = {
    "email": "admin@feemaster.edu",
    "password": "admin123",
    "role": "super_admin",
    "is_active": True,
    "is_verified": True
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash password"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get user from users table
        result = await db.execute_query(
            "users",
            "select",
            filters={"id": user_id},
            select_fields="*"
        )
        
        if not result["success"] or not result["data"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = result["data"][0]
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        return user
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Authenticate user and return access token"""
    try:
        logger.info(f"Login attempt for email: {user_credentials.email}")
        
        # Check for test user (development only)
        if settings.debug and user_credentials.email == TEST_USER["email"] and user_credentials.password == TEST_USER["password"]:
            logger.info("Test user login successful")
            access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
            access_token = create_access_token(
                data={"sub": "test-user-id", "email": TEST_USER["email"], "role": TEST_USER["role"]},
                expires_delta=access_token_expires
            )
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,  # Convert to seconds
                "user": {
                    "id": "test-user-id",
                    "email": TEST_USER["email"],
                    "role": TEST_USER["role"],
                    "is_active": TEST_USER["is_active"],
                    "is_verified": TEST_USER["is_verified"]
                }
            }
        
        # Normal login flow with PostgreSQL
        try:
            # Get user from database
            result = await db.execute_query(
                "users",
                "select",
                filters={"email": user_credentials.email},
                select_fields="*"
            )
            
            if not result["success"] or not result["data"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            user = result["data"][0]
            
            # Verify password
            if not verify_password(user_credentials.password, user.get("password_hash", "")):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            if not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is inactive"
                )
            
            # Update last login
            await db.execute_query(
                "users",
                "update",
                filters={"id": user["id"]},
                data={"last_login": datetime.utcnow().isoformat()}
            )
            
            # Create access token
            access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
            access_token = create_access_token(
                data={"sub": user["id"], "email": user["email"], "role": user.get("role", "user")},
                expires_delta=access_token_expires
            )
            
            # Remove sensitive data from user object
            user_data = {k: v for k, v in user.items() if k not in ["password_hash", "password"]}
            
            logger.info(f"Login successful for user: {user.get('id')}")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "user": user_data
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database authentication failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/register", response_model=APIResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = await db.execute_query(
            "users",
            "select",
            filters={"email": user_data.email},
            select_fields="id"
        )
        
        if existing_user["success"] and existing_user["data"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        user_dict = user_data.dict()
        user_dict["password_hash"] = hashed_password
        user_dict["created_at"] = datetime.utcnow().isoformat()
        user_dict["is_active"] = True
        user_dict["is_verified"] = True  # For now, auto-verify
        
        # Remove plain password
        user_dict.pop("password", None)
        
        result = await db.execute_query("users", "insert", data=user_dict)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        created_user = result["data"][0]
        
        # Remove sensitive data
        user_response = {k: v for k, v in created_user.items() if k not in ["password_hash", "password"]}
        
        return APIResponse(
            success=True,
            message="User registered successfully",
            data=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout", response_model=APIResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    # In a stateless JWT system, logout is handled client-side
    # You could implement a blacklist if needed
    return APIResponse(
        success=True,
        message="Logged out successfully"
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user["id"], "email": current_user["email"], "role": current_user.get("role", "user")},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": current_user
    } 