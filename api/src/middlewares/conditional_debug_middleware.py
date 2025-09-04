import json
import logging
import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time

logger = logging.getLogger(__name__)

class ConditionalDebugMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log raw request data only when debugging is enabled.
    
    Enable via environment variable: DEBUG_API_REQUESTS=true
    Or enable for specific endpoints: DEBUG_ENDPOINTS=trade-signals,orders
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Check if debugging is enabled
        self.debug_enabled = os.getenv('DEBUG_API_REQUESTS', 'false').lower() == 'true'
        
        # Check for specific endpoint debugging
        debug_endpoints = os.getenv('DEBUG_ENDPOINTS', '')
        self.debug_endpoints = [ep.strip() for ep in debug_endpoints.split(',') if ep.strip()]
        
        # Log initialization with debug info
        debug_requests_env = os.getenv('DEBUG_API_REQUESTS', 'false')
        debug_endpoints_env = os.getenv('DEBUG_ENDPOINTS', '')
        
        logger.info(f"🔧 Environment check: DEBUG_API_REQUESTS='{debug_requests_env}', DEBUG_ENDPOINTS='{debug_endpoints_env}'")
        
        if self.debug_enabled:
            logger.info("🔧 API Request debugging enabled globally")
        elif self.debug_endpoints:
            logger.info(f"🔧 API Request debugging enabled for endpoints: {self.debug_endpoints}")
        else:
            logger.info("🔧 API Request debugging disabled")
    
    def should_debug_request(self, request: Request) -> bool:
        """Check if this request should be debugged"""
        if not request.method == "POST":
            return False
            
        # Global debugging enabled
        if self.debug_enabled:
            return True
            
        # Check specific endpoint debugging
        if self.debug_endpoints:
            path = str(request.url.path)
            for endpoint in self.debug_endpoints:
                if endpoint in path:
                    return True
                    
        return False
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Only log if debugging is enabled for this request
        if self.should_debug_request(request):
            await self.log_request(request)
        
        # Process the request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response if debugging is enabled
            if self.should_debug_request(request):
                if response.status_code == 422:
                    logger.error(f"❌ Validation failed (422) for {request.url.path}")
                elif response.status_code >= 400:
                    logger.error(f"❌ Request failed ({response.status_code}) for {request.url.path}")
                else:
                    logger.info(f"✅ Request successful ({response.status_code}) for {request.url.path}")
                
                logger.info(f"⏱️ Request processed in {process_time:.3f}s")
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            if self.should_debug_request(request):
                logger.error(f"❌ Exception in request processing: {e}")
                logger.error(f"⏱️ Failed after {process_time:.3f}s")
            raise
    
    async def log_request(self, request: Request):
        """Log request details for debugging"""
        try:
            # Read the request body
            body = await request.body()
            
            if body:
                try:
                    json_data = json.loads(body.decode('utf-8'))
                    logger.info(f"📥 DEBUG Raw POST request to {request.url.path}:")
                    logger.info(f"📊 Request body: {json.dumps(json_data, indent=2)}")
                    
                    # Field-by-field analysis for trade-signals endpoint
                    if "/trade-signals" in str(request.url.path):
                        logger.info("🔍 Field analysis for trade signal:")
                        for key, value in json_data.items():
                            logger.info(f"   {key}: {value} (type: {type(value).__name__})")
                            if isinstance(value, str):
                                logger.info(f"     └─ length: {len(value)}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse request body as JSON: {e}")
                    logger.info(f"📊 Raw body: {body.decode('utf-8', errors='replace')}")
            else:
                logger.info(f"📥 DEBUG POST request to {request.url.path} with empty body")
            
            # Recreate the request with the body for downstream processing
            async def receive():
                return {"type": "http.request", "body": body}
            
            request._receive = receive
            
        except Exception as e:
            logger.error(f"❌ Error processing request body: {e}")

# Environment variable configuration helper
def is_debug_enabled() -> bool:
    """Check if API debugging is enabled"""
    return os.getenv('DEBUG_API_REQUESTS', 'false').lower() == 'true'

def get_debug_endpoints() -> list:
    """Get list of endpoints with debugging enabled"""
    debug_endpoints = os.getenv('DEBUG_ENDPOINTS', '')
    return [ep.strip() for ep in debug_endpoints.split(',') if ep.strip()] 