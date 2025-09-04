from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class OrderCancellationResponse(BaseModel):
    """Response schema for order cancellations"""
    id: UUID
    
    # Bot identification
    bot_name: str
    symbol: str
    
    # Cancellation details
    ibkr_order_id: int
    reason: str
    
    # Timestamps
    cancelled_time: datetime

    class Config:
        from_attributes = True 