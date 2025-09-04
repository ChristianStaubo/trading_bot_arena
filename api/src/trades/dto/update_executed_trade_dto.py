from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"


class UpdateExecutedTradeDto(BaseModel):
    """DTO for updating an executed trade"""
    status: Optional[OrderStatus] = Field(None, description="Order status")
    filled_quantity: Optional[int] = Field(None, ge=0, description="Filled quantity")
    avg_fill_price: Optional[float] = Field(None, gt=0, description="Average fill price")
    remaining_quantity: Optional[int] = Field(None, ge=0, description="Remaining quantity")
    fill_time: Optional[datetime] = Field(None, description="Fill timestamp")
    commission: Optional[float] = Field(None, description="Commission paid")
    realized_pnl: Optional[float] = Field(None, description="Realized P&L")
    error_message: Optional[str] = Field(None, description="Error message if any") 