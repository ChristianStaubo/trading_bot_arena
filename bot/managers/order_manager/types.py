from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class OrderInfo:
    """Information about an active order"""
    order_id: int
    symbol: str
    action: str  # 'BUY' or 'SELL'
    order_type: str  # 'MARKET', 'LIMIT', 'OCO'
    quantity: int
    entry_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    timestamp: datetime = None
    status: str = 'PENDING'  # 'PENDING', 'FILLED', 'CANCELLED', 'REJECTED'
    tp_order_id: Optional[int] = None  # Take profit order ID
    sl_order_id: Optional[int] = None  # Stop loss order ID

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Position:
    """Information about an active position"""
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    size: int
    entry_price: float
    entry_time: datetime
    take_profit: float
    stop_loss: float
    entry_order_id: int
    tp_order_id: Optional[int] = None
    sl_order_id: Optional[int] = None
    unrealized_pnl: float = 0.0

    def update_pnl(self, current_price: float):
        """Update unrealized PnL based on current price"""
        if self.direction == 'LONG':
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.size