from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to authenticate requests using API key.
    
    Checks for API key in X-API-Key or Authorization headers.
    Returns 401 Unauthorized if API key is missing or invalid.
    """
    
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for health check (optional - remove if you want to protect this too)
        if request.url.path == "/api/v1/health":
            return await call_next(request)
        
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        if not api_key or api_key != self.api_key:
            return JSONResponse(
                content={
                    "error": "Unauthorized", 
                    "message": "Valid API key required. Include 'X-API-Key' header with your request."
                }, 
                status_code=401
            )
        
        return await call_next(request)
