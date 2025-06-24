# Supabase auth removed - using backend-based authentication
# from .supabase_auth import get_current_user, get_optional_user, supabase_auth

# Import from routes.auth instead
from ..routes.auth import get_current_user

# For optional user, we can create a simple wrapper
async def get_optional_user(credentials=None):
    """Get current user if authenticated, otherwise return None"""
    try:
        if credentials:
            return await get_current_user(credentials)
        return None
    except:
        return None

__all__ = ["get_current_user", "get_optional_user"] 