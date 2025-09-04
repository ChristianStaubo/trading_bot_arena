import logging
from fastapi import APIRouter

logger = logging.getLogger("api")

router = APIRouter(tags=["health"])

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check endpoint called")
    return "pong"