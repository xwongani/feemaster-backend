# Optional imports for cache service
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Redis not available - caching will be disabled")

import json
import logging
from typing import Any, Optional
from datetime import datetime, timedelta
from ..config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available - caching disabled")
                return
                
            if settings.redis_url:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    password=settings.redis_password,
                    decode_responses=True
                )
                logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.redis_client:
                return None
                
            value = await self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            if not self.redis_client:
                return False
                
            ttl = ttl or self.default_ttl
            await self.redis_client.set(
                key,
                json.dumps(value),
                ex=ttl
            )
            return True
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if not self.redis_client:
                return False
                
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern"""
        try:
            if not self.redis_client:
                return False
                
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache clear pattern failed for {pattern}: {e}")
            return False
    
    def get_key(self, prefix: str, *args) -> str:
        """Generate cache key"""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"
    
    async def get_or_set(self, key: str, getter_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or set if not exists"""
        value = await self.get(key)
        if value is None:
            value = await getter_func()
            if value is not None:
                await self.set(key, value, ttl)
        return value

# Create cache service instance
cache_service = CacheService() 