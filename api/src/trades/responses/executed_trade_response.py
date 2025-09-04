from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class ExecutedTradeResponse(BaseModel):
    """Response schema for executed trades"""
    id: UUID
    
    # Link to order that created this execution
    order_id_ref: Optional[UUID]
    
    # Bot identification
    bot_name: str
    symbol: str
    
    # IBKR Trade object fields
    ibkr_order_id: int
    ibkr_contract_id: Optional[int]
    ibkr_parent_order_id: Optional[int]
    
    # Order details from trade.order
    action: str
    order_type: str
    order_purpose: Optional[str]
    total_quantity: int
    limit_price: Optional[float]
    aux_price: Optional[float]
    entry_price: Optional[float]
    
    # OrderStatus details from trade.orderStatus
    status: str
    filled_quantity: int
    remaining_quantity: int
    avg_fill_price: Optional[float]
    last_fill_price: Optional[float]
    
    # Financial details
    commission: Optional[float]
    realized_pnl: Optional[float]
    unrealized_pnl: Optional[float]
    
    # Timestamps
    order_time: Optional[datetime]
    fill_time: datetime
    last_update_time: datetime
    
    # Additional IBKR data
    account: Optional[str]
    exchange: Optional[str]
    currency: Optional[str]

    class Config:
        from_attributes = True 