from pydantic import BaseModel, Field
from typing import Optional


class CreateOrderCancellationDto(BaseModel):
    """DTO for creating a new order cancellation record"""
    
    # Bot identification
    bot_name: str = Field(..., min_length=1, max_length=100, description="Bot name/identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    
    # Cancellation details
    ibkr_order_id: int = Field(..., description="IBKR order ID that was cancelled")
    reason: str = Field(..., max_length=50, description="Cancellation reason (strategy_cancel, manual_cancel, timeout, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "bot_name": "es_bollinger_bands",
                "symbol": "ES",
                "ibkr_order_id": 12345,
                "reason": "strategy_cancel"
            }
        } 