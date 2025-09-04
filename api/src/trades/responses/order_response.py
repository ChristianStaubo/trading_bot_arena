from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class OrderResponse(BaseModel):
    """Response schema for orders"""
    id: UUID
    
    # Link to trade signal that generated this order
    trade_signal_id: Optional[UUID]
    
    # Bot identification
    bot_name: str
    symbol: str
    
    # PlaceOrderResult fields
    success: bool
    error: Optional[str]
    parent_order_id: Optional[int]
    
    # Order details
    order_type: Optional[str]
    quantity: Optional[int]
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # IBKR Trade objects count (for bracket orders)
    trade_count: Optional[int]
    
    # Timestamps
    timestamp: datetime

    class Config:
        from_attributes = True 