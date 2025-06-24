from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
import jwt
import bcrypt
import logging
from supabase import create_client, Client

from ..models import UserLogin, UserCreate, Token, User, APIResponse
from ..database import db
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

# Test user credentials (for development only)
TEST_USER = {
    "email": "test@feemaster.com",
    "password": "test123",
    "role": "admin",
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
        
        # Get user from profiles table (Supabase Auth integration)
        result = await db.execute_query(
            "profiles",
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
        
        # Normal login flow with Supabase
        try:
            # Attempt to sign in with Supabase
            response = supabase.auth.sign_in_with_password({
                "email": user_credentials.email,
                "password": user_credentials.password
            })
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Get user data from profiles table
            result = await db.execute_query(
                "profiles",
                "select",
                filters={"id": response.user.id},
                select_fields="*"
            )
            
            if not result["success"] or not result["data"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User profile not found in database"
                )
            
            user = result["data"][0]
            
            if not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is inactive"
                )
            
            # Update last login
            await db.execute_query(
                "profiles",
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
            
        except Exception as e:
            logger.error(f"Supabase authentication failed: {str(e)}")
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
            detail="Login failed"
        )

@router.post("/register", response_model=APIResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        # Check if user already exists
        existing = await db.execute_query(
            "users",
            "select",
            filters={"email": user_data.email},
            select_fields="id"
        )
        
        if existing["success"] and existing["data"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = get_password_hash(user_data.password)
        
        # Create user data
        user_dict = user_data.dict()
        del user_dict["password"]
        user_dict.update({
            "password_hash": password_hash,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "is_verified": False
        })
        
        # Insert user
        result = await db.execute_query("users", "insert", data=user_dict)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        return APIResponse(
            success=True,
            message="User registered successfully",
            data={"user_id": result["data"][0]["id"]}
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout", response_model=APIResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    return APIResponse(
        success=True,
        message="Logged out successfully"
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh access token"""
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": current_user["id"], "email": current_user["email"], "role": current_user["role"]},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": current_user
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed") 