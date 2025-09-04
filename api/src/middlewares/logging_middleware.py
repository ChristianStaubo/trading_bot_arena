import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context and log HTTP requests
    Similar to NestJS logging interceptors
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"Incoming request",
            extra={
                'request_id': request_id,
                'method': request.method,
                'url': str(request.url),
                'client_ip': request.client.host if request.client else None,
                'user_agent': request.headers.get('user-agent'),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'url': str(request.url),
                    'status_code': response.status_code,
                    'process_time_ms': round(process_time * 1000, 2),
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'url': str(request.url),
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'process_time_ms': round(process_time * 1000, 2),
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise


def get_request_id(request: Request) -> str:
    """
    Get the request ID from the request state
    """
    return getattr(request.state, 'request_id', 'unknown')


# Helper function to add request context to logger
def get_logger_with_request_context(name: str, request: Request = None) -> logging.Logger:
    """
    Get a logger with request context added
    """
    logger = logging.getLogger(name)
    
    if request:
        request_id = get_request_id(request)
        # You can extend this to add more request context
        logger = logger.getChild(f"req_{request_id}")
    
    return logger 