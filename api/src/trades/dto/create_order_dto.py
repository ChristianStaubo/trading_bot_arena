from pydantic import BaseModel, Field
from typing import Optional


class CreateOrderDto(BaseModel):
    """DTO for creating a new order record"""
    
    # Bot identification
    bot_name: str = Field(..., min_length=1, max_length=100, description="Bot name/identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol (e.g., ES, EURUSD)")
    
    # PlaceOrderResult fields
    success: bool = Field(..., description="Whether order placement was successful")
    error: Optional[str] = Field(None, description="Error message if order placement failed")
    
    # Order details
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    
    # IBKR Trade objects count (for bracket orders)
    trade_count: Optional[int] = Field(None, ge=0, description="Number of trades in bracket order")

    class Config:
        json_schema_extra = {
            "example": {
                "bot_name": "es_bollinger_bands",
                "symbol": "ES",
                "success": True,
                "error": None,
                "stop_loss": 4145.25,
                "take_profit": 4155.25,
                "trade_count": 3
            }
        } 