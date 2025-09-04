"""
Notification Manager Type Definitions

Defines types and enums for notification operations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class NotificationLevel(Enum):
    """Notification severity levels"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class NotificationSettings:
    """Type-safe notification configuration"""
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]
    enabled: bool
    min_level: NotificationLevel


class EventType(Enum):
    """Types of trading events that can trigger notifications"""
    # Trade execution events
    TRADE_SIGNAL = "trade_signal"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    
    # Connection events
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    
    # System events
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    ERROR_OCCURRED = "error_occurred"


@dataclass(frozen=True)
class NotificationEvent:
    """Container for notification event data"""
    event_type: EventType
    level: NotificationLevel
    title: str
    message: str
    bot_name: str
    symbol: str
    strategy_name: str
    timestamp: datetime
    
    # Optional fields for specific event types
    order_id: Optional[int] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    pnl: Optional[float] = None
    error_details: Optional[str] = None