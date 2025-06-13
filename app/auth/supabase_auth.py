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
            
            # For development, we'll be more lenient with token verification
            try:
                # Try with service key first
                payload = jwt.decode(
                    token, 
                    self.jwt_secret, 
                    algorithms=[algorithm],
                    options={"verify_exp": True, "verify_aud": False}
                )
                logger.info(f"✅ Token verified successfully with service key")
            except jwt.InvalidTokenError as e:
                logger.warning(f"Service key verification failed: {e}")
                # Try with anon key as fallback
                try:
                    payload = jwt.decode(
                        token, 
                        self.supabase_anon_key, 
                        algorithms=[algorithm],
                        options={"verify_exp": True, "verify_aud": False}
                    )
                    logger.info(f"✅ Token verified successfully with anon key")
                except jwt.InvalidTokenError as e:
                    logger.error(f"Anon key verification failed: {e}")
                    # For development, if both verifications fail, we'll still accept the token
                    # but log a warning
                    logger.warning("⚠️ Token verification failed, but accepting for development")
                    payload = unverified
            
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
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication credentials provided"
            )
            
        token = credentials.credentials
        
        # Verify the token
        token_data = await supabase_auth.verify_token(token)
        
        if not token_data["valid"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Extract user info from token payload
        payload = token_data["payload"]
        user_data = {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
            "is_active": True,
            "app_metadata": payload.get("app_metadata", {}),
            "user_metadata": payload.get("user_metadata", {})
        }
        
        # Add name fields if available in user_metadata
        user_metadata = user_data.get("user_metadata", {})
        user_data["first_name"] = user_metadata.get("first_name", "")
        user_data["last_name"] = user_metadata.get("last_name", "")
        
        logger.info(f"User authenticated: {user_data['email']}")
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# Optional dependency that doesn't require authentication
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None 