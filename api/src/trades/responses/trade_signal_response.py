from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class TradeSignalResponse(BaseModel):
    """Response schema for trade signals"""
    id: UUID
    
    # Bot identification
    bot_name: str
    symbol: str
    strategy_name: str
    timeframe: str
    
    # Signal details
    action: str  # BUY/SELL
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Optional signal metadata
    confidence: Optional[float]
    reason: Optional[str]
    
    # Concurrent trade management
    max_concurrent_trades: int
    current_active_trades: int
    order_placed: bool
    
    # Timestamps
    timestamp: datetime

    class Config:
        from_attributes = True 