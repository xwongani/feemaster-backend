from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import logging
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
security = HTTPBearer()

class SupabaseAuth:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY") 
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        # Validate that we have the keys
        if not self.supabase_service_key:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable is not set")
        if not self.supabase_anon_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is not set")
        
        # JWT secret is usually the service key for Supabase
        self.jwt_secret = self.supabase_service_key
        logger.info(f"Supabase auth initialized. Service key length: {len(self.jwt_secret)}")
        logger.info(f"Supabase auth initialized. Anon key length: {len(self.supabase_anon_key)}")
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Supabase JWT token"""
        try:
            # Ensure token is a string and strip whitespace
            token = str(token).strip()
            logger.info(f"Attempting to verify token: {token[:20]}...")
            
            # Try to decode without verification first to get algorithm
            unverified = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"Token payload preview: {unverified}")
            
            # Most Supabase tokens use HS256
            algorithm = unverified.get("alg", "HS256")
            logger.info(f"Token algorithm: {algorithm}")
            
            # Use the keys directly
            service_key = self.jwt_secret
            anon_key = self.supabase_anon_key
            
            logger.info(f"Service key length: {len(service_key)}")
            logger.info(f"Anon key length: {len(anon_key)}")
            
            # For development, let's be more lenient
            try:
                # Try with service key
                payload = jwt.decode(
                    token, 
                    service_key, 
                    algorithms=[algorithm],
                    options={"verify_exp": True, "verify_aud": False}
                )
                logger.info(f"✅ Token verified successfully with service key")
            except jwt.InvalidTokenError as e:
                logger.warning(f"Service key verification failed: {e}")
                # Try with anon key as fallback
                payload = jwt.decode(
                    token, 
                    anon_key, 
                    algorithms=[algorithm],
                    options={"verify_exp": True, "verify_aud": False}
                )
                logger.info(f"✅ Token verified successfully with anon key")
            
            return {
                "valid": True,
                "payload": payload,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role", "authenticated")
            }
            
        except jwt.ExpiredSignatureError:
            logger.error("❌ Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        except Exception as e:
            logger.error(f"❌ Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

# Create global instance
supabase_auth = SupabaseAuth()

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Dict[str, Any]:
    """Get current authenticated user from Supabase token"""
    
    # 🚨 TEMPORARILY DISABLED FOR DEVELOPMENT 🚨
    # Return a dummy user to bypass authentication during development
    logger.info("⚠️  Authentication temporarily disabled - returning dummy user")
    return {
        "id": "dev-user-id", 
        "email": "dev@example.com",
        "role": "admin",
        "is_active": True,
        "app_metadata": {"role": "admin"},
        "user_metadata": {"first_name": "Dev", "last_name": "User"},
        "first_name": "Dev",
        "last_name": "User"
    }
    
    # Original authentication code (commented out)
    # try:
    #     token = credentials.credentials
    #     
    #     # Verify the token
    #     token_data = await supabase_auth.verify_token(token)
    #     
    #     if not token_data["valid"]:
    #         raise HTTPException(
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #             detail="Invalid authentication token"
    #         )
    #     
    #     # Extract user info from token payload
    #     payload = token_data["payload"]
    #     user_data = {
    #         "id": payload.get("sub"),
    #         "email": payload.get("email"),
    #         "role": payload.get("role", "authenticated"),
    #         "is_active": True,
    #         "app_metadata": payload.get("app_metadata", {}),
    #         "user_metadata": payload.get("user_metadata", {})
    #     }
    #     
    #     # Add name fields if available in user_metadata
    #     user_metadata = user_data.get("user_metadata", {})
    #     user_data["first_name"] = user_metadata.get("first_name", "")
    #     user_data["last_name"] = user_metadata.get("last_name", "")
    #     
    #     logger.info(f"User authenticated: {user_data['email']}")
    #     return user_data
    #     
    # except HTTPException:
    #     raise
    # except Exception as e:
    #     logger.error(f"Authentication error: {e}")
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Authentication failed"
    #     )

# Optional dependency that doesn't require authentication
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None 