import json
import logging
from fastapi import Request, Depends
from typing import Optional

logger = logging.getLogger(__name__)

class RequestDebugger:
    """Dependency class for debugging FastAPI requests"""
    
    def __init__(self, endpoint_name: str = None):
        self.endpoint_name = endpoint_name
    
    async def __call__(self, request: Request) -> None:
        """Log request details for debugging"""
        if request.method == "POST":
            endpoint = self.endpoint_name or "unknown"
            
            try:
                # Read and log the raw request body
                body = await request.body()
                
                if body:
                    try:
                        json_data = json.loads(body.decode('utf-8'))
                        logger.info(f"📥 DEBUG [{endpoint}] Raw request:")
                        logger.info(f"📊 Request body: {json.dumps(json_data, indent=2)}")
                        
                        # Field-by-field analysis
                        logger.info(f"🔍 Field analysis:")
                        for key, value in json_data.items():
                            logger.info(f"   {key}: {value} (type: {type(value).__name__})")
                            if isinstance(value, str):
                                logger.info(f"     └─ length: {len(value)}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse request body as JSON: {e}")
                        logger.info(f"📊 Raw body: {body.decode('utf-8', errors='replace')}")
                else:
                    logger.info(f"📥 DEBUG [{endpoint}] Empty request body")
                    
                # Recreate the request with body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
                
            except Exception as e:
                logger.error(f"❌ Error in debug dependency for [{endpoint}]: {e}")

# Convenience functions for different endpoints
def debug_trade_signals():
    """Debug dependency for trade signals endpoint"""
    return RequestDebugger("trade_signals")

def debug_orders():
    """Debug dependency for orders endpoint"""  
    return RequestDebugger("orders")

def debug_executed_trades():
    """Debug dependency for executed trades endpoint"""
    return RequestDebugger("executed_trades")

def debug_endpoint(name: str):
    """Generic debug dependency with custom endpoint name"""
    return RequestDebugger(name) 