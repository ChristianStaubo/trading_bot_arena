from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateTradeSignalDto(BaseModel):
    """DTO for creating a new trade signal"""
    
    # Bot identification
    bot_name: str = Field(..., min_length=1, max_length=100, description="Bot name/identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol (e.g., ES, EURUSD)")
    strategy_name: str = Field(..., min_length=1, max_length=100, description="Name of the trading strategy")
    timeframe: str = Field(..., min_length=1, max_length=20, description="Timeframe (e.g., ONE_MIN, FIVE_MIN)")
    
    # Signal details
    action: str = Field(..., description="Signal action: BUY or SELL")
    entry_price: float = Field(..., gt=0, description="Signal entry price")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price level")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price level")
    
    # Optional signal metadata
    reason: Optional[str] = Field(None, max_length=500, description="Reason why signal was generated")
    
    # Concurrent trade management
    max_concurrent_trades: int = Field(..., ge=1, description="Maximum concurrent trades allowed")
    current_active_trades: int = Field(..., ge=0, description="Current number of active trades")

    class Config:
        json_schema_extra = {
            "example": {
                "bot_name": "es_bollinger_bands",
                "symbol": "ES",
                "strategy_name": "bollinger_bands",
                "timeframe": "ONE_MIN",
                "action": "BUY",
                "entry_price": 4150.25,
                "stop_loss": 4145.25,
                "take_profit": 4155.25,
                "reason": "Bollinger band breakout with volume confirmation",
                "max_concurrent_trades": 1,
                "current_active_trades": 0
            }
        } 