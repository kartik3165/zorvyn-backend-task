from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from starlette.responses import JSONResponse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

EXCLUDED_PATH_PREFIXES = (
    "/auth/login",
    "/auth/signup",
    "/auth/refresh",
    "/auth/logout",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        if request.method in SAFE_METHODS:
            return await call_next(request)

        path = request.url.path

        if any(path.startswith(p) for p in EXCLUDED_PATH_PREFIXES):
            return await call_next(request)

        access_token = request.cookies.get("access_token")
        if not access_token:
            return await call_next(request)

        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")

        if not cookie_token or not header_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        if cookie_token != header_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid CSRF token"},
            )

        return await call_next(request)