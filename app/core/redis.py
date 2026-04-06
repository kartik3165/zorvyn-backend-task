import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def check_redis_connection() -> None:
    await redis_client.ping()


async def close_redis_connection() -> None:
    await redis_client.aclose()
