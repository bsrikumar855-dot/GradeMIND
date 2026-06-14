from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings
from app.core.security import decode_access_token


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Optional middleware to check for Authorization headers and validate JWT structure on requests.
    Stores user payload in request.state.user for downstream access.
    """
    async def dispatch(self, request: Request, call_next):
        if not settings.AUTH_ENABLED:
            return await call_next(request)

        # Exclude docs/openapi/health paths from strict checks in middleware if needed,
        # but here we only validate the token if the header is present, allowing standard route dependencies to handle missing auth.
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                payload = decode_access_token(token)
                if not payload:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "success": False,
                            "message": "Invalid or expired authorization token"
                        }
                    )
                # Store payload in request state
                request.state.user = payload
                
        return await call_next(request)
