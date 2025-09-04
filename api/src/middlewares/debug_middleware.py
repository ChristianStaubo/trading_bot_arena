import json
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time

logger = logging.getLogger(__name__)

class DebugRequestMiddleware(BaseHTTPMiddleware):
    """Middleware to log raw request data for debugging validation errors"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log raw request data for POST requests (where validation happens)
        if request.method == "POST":
            # Read the request body
            body = await request.body()
            
            try:
                # Try to parse as JSON for pretty logging
                if body:
                    json_data = json.loads(body.decode('utf-8'))
                    logger.info(f"📥 Raw POST request to {request.url.path}:")
                    logger.info(f"📊 Request body: {json.dumps(json_data, indent=2)}")
                    
                    # Log specific field analysis for trade-signals endpoint
                    if "/trade-signals" in str(request.url.path):
                        logger.info("🔍 Field analysis for trade signal:")
                        for key, value in json_data.items():
                            logger.info(f"   {key}: {value} (type: {type(value).__name__})")
                            if isinstance(value, str):
                                logger.info(f"     └─ length: {len(value)}")
                else:
                    logger.info(f"📥 POST request to {request.url.path} with empty body")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse request body as JSON: {e}")
                logger.info(f"📊 Raw body: {body.decode('utf-8', errors='replace')}")
            except Exception as e:
                logger.error(f"❌ Error processing request body: {e}")
            
            # We need to recreate the request with the body for downstream processing
            # Since we've already consumed the body
            async def receive():
                return {"type": "http.request", "body": body}
            
            request._receive = receive
        
        # Process the request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log the response status
            if request.method == "POST":
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
            logger.error(f"❌ Exception in request processing: {e}")
            logger.error(f"⏱️ Failed after {process_time:.3f}s")
            raise 