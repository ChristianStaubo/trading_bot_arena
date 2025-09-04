from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ExecutedTradeSummaryResponse(BaseModel):
    """Summary response for executed trades list"""
    id: UUID
    bot_name: str
    symbol: str
    action: str  # BUY/SELL
    ibkr_order_id: int
    total_quantity: int
    filled_quantity: int
    avg_fill_price: float
    status: str
    fill_time: datetime

    class Config:
        from_attributes = True 