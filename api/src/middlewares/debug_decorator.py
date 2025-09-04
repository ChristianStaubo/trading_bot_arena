import json
import logging
import functools
from typing import Callable
from fastapi import Request
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)

def debug_request(endpoint_name: str = None):
    """
    Decorator to add request debugging to specific FastAPI endpoints.
    
    Usage:
        @debug_request("trade_signals")
        @router.post("/trade-signals")
        async def create_trade_signal(dto: CreateTradeSignalDto, db: AsyncSession = Depends(get_db)):
            ...
    
    Args:
        endpoint_name: Optional name for logging context
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the Request object in the arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # If no Request in args, check kwargs
            if request is None:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request and request.method == "POST":
                endpoint = endpoint_name or func.__name__
                
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
                    logger.error(f"❌ Error in debug decorator for [{endpoint}]: {e}")
            
            # Call the original function
            try:
                result = await func(*args, **kwargs)
                if request and request.method == "POST":
                    endpoint = endpoint_name or func.__name__
                    logger.info(f"✅ DEBUG [{endpoint}] Request successful")
                return result
                
            except RequestValidationError as e:
                if request and request.method == "POST":
                    endpoint = endpoint_name or func.__name__
                    logger.error(f"🚨 DEBUG [{endpoint}] VALIDATION ERROR:")
                    for error in e.errors():
                        logger.error(f"   Field: {' -> '.join(str(loc) for loc in error['loc'])}")
                        logger.error(f"   Error: {error['msg']}")
                        logger.error(f"   Type: {error['type']}")
                        if 'input' in error:
                            logger.error(f"   Input: {error['input']} (type: {type(error['input']).__name__})")
                        logger.error("   " + "-" * 40)
                raise
            except Exception as e:
                if request and request.method == "POST":
                    endpoint = endpoint_name or func.__name__
                    logger.error(f"❌ DEBUG [{endpoint}] Exception: {e}")
                raise
                
        return wrapper
    return decorator

def debug_dto_fields(dto_class):
    """
    Helper decorator to log DTO field validation requirements.
    
    Usage:
        @debug_dto_fields(CreateTradeSignalDto)
        @debug_request("trade_signals")  
        @router.post("/trade-signals")
        async def create_trade_signal(dto: CreateTradeSignalDto, ...):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Log DTO field requirements for debugging
            logger.info(f"📋 DTO Field Requirements for {dto_class.__name__}:")
            
            if hasattr(dto_class, '__annotations__'):
                for field_name, field_type in dto_class.__annotations__.items():
                    logger.info(f"   {field_name}: {field_type}")
            
            if hasattr(dto_class, '__fields__'):
                for field_name, field_info in dto_class.__fields__.items():
                    logger.info(f"   {field_name}: required={field_info.is_required()}")
                    
            return await func(*args, **kwargs)
        return wrapper
    return decorator 