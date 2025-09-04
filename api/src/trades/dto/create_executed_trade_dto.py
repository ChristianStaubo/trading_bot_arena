from pydantic import BaseModel, Field
from typing import Optional


class CreateExecutedTradeDto(BaseModel):
    """DTO for creating a new executed trade record"""
    
    # Bot identification
    bot_name: str = Field(..., min_length=1, max_length=100, description="Bot name/identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    
    # IBKR Trade object fields
    ibkr_order_id: int = Field(..., description="IBKR order ID (trade.order.orderId)")
    ibkr_contract_id: Optional[int] = Field(None, description="IBKR contract ID (trade.contract.conId)")
    ibkr_parent_order_id: Optional[int] = Field(None, description="IBKR parent order ID (trade.order.parentId, 0 for entry orders)")
    
    # Order details from trade.order
    action: str = Field(..., description="BUY or SELL")
    order_type: str = Field(..., max_length=20, description="Order type (LMT, MKT, STP, etc.)")
    order_purpose: Optional[str] = Field(None, max_length=15, description="Order purpose: ENTRY, TAKE_PROFIT, or STOP_LOSS")
    total_quantity: int = Field(..., ge=1, description="Total order quantity")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price (trade.order.lmtPrice)")
    aux_price: Optional[float] = Field(None, gt=0, description="Auxiliary price/stop price (trade.order.auxPrice)")
    
    # OrderStatus details from trade.orderStatus
    status: str = Field(..., max_length=20, description="Order status (Filled, Cancelled, etc.)")
    filled_quantity: int = Field(..., ge=0, description="Quantity filled")
    remaining_quantity: int = Field(..., ge=0, description="Remaining quantity")
    avg_fill_price: Optional[float] = Field(None, gt=0, description="Average fill price")
    last_fill_price: Optional[float] = Field(None, gt=0, description="Last fill price")
    
    # Financial details
    commission: Optional[float] = Field(None, description="Commission paid")
    realized_pnl: Optional[float] = Field(None, description="Realized P&L")
    
    # Additional IBKR data
    exchange: Optional[str] = Field(None, max_length=20, description="Exchange")
    currency: Optional[str] = Field(None, max_length=10, description="Currency")

    class Config:
        json_schema_extra = {
            "example": {
                "bot_name": "es_bollinger_bands",
                "symbol": "ES",
                "ibkr_order_id": 12345,
                "ibkr_contract_id": 67890,
                "ibkr_parent_order_id": 0,
                "action": "BUY",
                "order_type": "LMT",
                "order_purpose": "ENTRY",
                "total_quantity": 1,
                "limit_price": 4150.25,
                "aux_price": None,
                "status": "Filled",
                "filled_quantity": 1,
                "remaining_quantity": 0,
                "avg_fill_price": 4150.50,
                "last_fill_price": 4150.50,
                "commission": 2.25,
                "realized_pnl": 0.25,
                "exchange": "CME",
                "currency": "USD"
            }
        } 