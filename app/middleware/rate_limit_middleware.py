from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.redis import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.max_requests = settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
        self._excluded_paths = {"/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in self._excluded_paths:
            return await call_next(request)

        identifier = self._get_client_identifier(request)
        key = f"rate_limit:{identifier}"

        try:
            current_count = await redis_client.incr(key)
            if current_count == 1:
                await redis_client.expire(key, self.window_seconds)

            ttl = await redis_client.ttl(key)
        except Exception:
            return await call_next(request)

        ttl = max(ttl, 0)
        remaining = max(self.max_requests - current_count, 0)

        if current_count > self.max_requests:
            retry_after = ttl or self.window_seconds
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Rate limit exceeded. Please try again later.",
                    "data": None,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        response = await call_next(request)
        reset_in = ttl or self.window_seconds
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response

    def _get_client_identifier(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client and request.client.host:
            return request.client.host

        return "anonymous"
