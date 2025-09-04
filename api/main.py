from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
import logging
import os

# Logtail direct integration
from logtail import LogtailHandler

from src.middlewares.transform_response import TransformResponseMiddleware
from src.middlewares.conditional_debug_middleware import ConditionalDebugMiddleware
from src.middlewares.api_key_middleware import APIKeyMiddleware

from src.trades.api import router as trades_router
from src.api import router as base_router
from database import engine, Base

# Create FastAPI application
app = FastAPI(
    title="Trading Bot API",
    description="FastAPI backend for logging trading bot data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # Add Swagger UI configuration for better UX
    swagger_ui_parameters={
        "persistAuthorization": True,  # Keep authorization between page refreshes
        "displayRequestDuration": True,  # Show request timing
    }
)



# Get API key from environment
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
if not API_SECRET_KEY:
    raise ValueError("API_SECRET_KEY environment variable is required but not set")

# Properly configure security schemes for OpenAPI
app.openapi_schema = None  # Reset to regenerate with security

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API Key authentication (IMPORTANT: Add this AFTER CORS but BEFORE other middlewares)
app.add_middleware(APIKeyMiddleware, api_key=API_SECRET_KEY)

# Add conditional debug middleware (controlled by environment variables)
app.add_middleware(ConditionalDebugMiddleware)
app.add_middleware(TransformResponseMiddleware)

# Set up logtail logging directly (following GitHub example)
def setup_api_logging():
    # Get environment variables
    source_token = os.getenv('LOGTAIL_SOURCE_TOKEN')
    host = os.getenv('LOGTAIL_HOST')
    
    print(f"Setting up logging - Token: {source_token[:8] if source_token else 'None'}...")
    print(f"Setting up logging - Host: {host}")
    
    # Create handler
    if source_token and host:
        logtail_handler = LogtailHandler(source_token=source_token, host=host)
        
        # Create logger
        logger = logging.getLogger("api")
        logger.handlers = []  # Clear existing handlers
        logger.setLevel(logging.DEBUG)  # Set minimal log level
        
        # Add both logtail and console handlers
        logger.addHandler(logtail_handler)  # Send to logtail
        
        # Also add console handler for local development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - API - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)  # Also log to console
        
        logger.propagate = False
        
        print("✅ Logtail handler added successfully!")
        print("✅ Console handler added for local development!")
        return logger
    else:
        print(f"❌ Missing logtail config - Token: {bool(source_token)}, Host: {bool(host)}")
        # Fallback to console logging
        logger = logging.getLogger("api")
        logger.handlers = []
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - API - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        logger.propagate = False
        return logger

api_logger = setup_api_logging()

# Custom validation error handler for debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom handler for validation errors to provide better debugging info"""
    validation_logger = logging.getLogger("api")
    
    validation_logger.error("🚨 VALIDATION ERROR DETAILS:")
    validation_logger.error(f"   URL: {request.url}")
    validation_logger.error(f"   Method: {request.method}")
    
    for error in exc.errors():
        validation_logger.error(f"   Field: {' -> '.join(str(loc) for loc in error['loc'])}")
        validation_logger.error(f"   Error: {error['msg']}")
        validation_logger.error(f"   Type: {error['type']}")
        if 'input' in error:
            validation_logger.error(f"   Input: {error['input']} (type: {type(error['input']).__name__})")
        if 'ctx' in error:
            validation_logger.error(f"   Context: {error['ctx']}")
        validation_logger.error("   " + "-" * 50)
    
    return JSONResponse(
        status_code=422,
        content={
            "statusCode": 422,
            "message": "Validation Error",
            "data": {"detail": exc.errors()}
        }
    )

# Include API routers
app.include_router(base_router, prefix="/api/v1")
app.include_router(trades_router, prefix="/api/v1")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize logging on startup"""
    api_logger.info("🚀 Trading Bot API started with logtail logging enabled")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await engine.dispose()
    api_logger.info("Database connections closed")

# Custom OpenAPI schema for better documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add any custom security schemes here if needed in the future
    openapi_schema["components"]["securitySchemes"] = {}
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 