from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class TradeSignalSummaryResponse(BaseModel):
    """Summary response for trade signals list"""
    id: UUID
    bot_name: str
    symbol: str
    strategy_name: str
    action: str  # BUY/SELL
    entry_price: float
    order_placed: bool
    timestamp: datetime

    class Config:
        from_attributes = True 