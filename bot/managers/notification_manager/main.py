"""
Notification Manager - Telegram Bot Notifications

Handles all notification operations for the trading bot.
Sends critical event notifications via Telegram bot.

Responsibilities:
- Send Telegram notifications for critical trading events
- Format messages with trade details and context
- Handle notification filtering and rate limiting
- Manage connection to Telegram Bot API
"""

import asyncio
import aiohttp
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from .types import NotificationEvent, NotificationLevel, EventType, NotificationSettings
from .utils import format_telegram_message, get_notification_settings, should_send_notification

if TYPE_CHECKING:
    from managers.logging_manager import CombinedLogger


class NotificationManager:
    """
    Manages notification delivery for trading bot events
    
    Responsibilities:
    - Send Telegram notifications for critical events
    - Format messages with trading context and details
    - Handle notification settings and filtering
    - Provide convenience methods for common events
    """
    
    def __init__(self, 
                 logger: 'CombinedLogger',
                 bot_name: str,
                 symbol: str,
                 strategy_name: str):
        """
        Initialize Notification Manager
        
        Args:
            logger: CombinedLogger instance for error reporting
            bot_name: Name of the bot instance
            symbol: Trading symbol
            strategy_name: Name of the trading strategy
        """
        self.logger: 'CombinedLogger' = logger
        self.bot_name: str = bot_name
        self.symbol: str = symbol
        self.strategy_name: str = strategy_name
        
        # Load notification settings
        self.settings: NotificationSettings = get_notification_settings()
        self.enabled: bool = self.settings.enabled
        self.telegram_bot_token: Optional[str] = self.settings.telegram_bot_token
        self.telegram_chat_id: Optional[str] = self.settings.telegram_chat_id
        self.min_level: NotificationLevel = self.settings.min_level
        
        # Validate configuration
        if self.enabled and (not self.telegram_bot_token or not self.telegram_chat_id):
            self.logger.warning("⚠️ [NOTIFICATIONS] Telegram credentials missing - notifications disabled")
            self.enabled = False
        elif self.enabled:
            self.logger.info(f"✅ [NOTIFICATIONS] Telegram notifications enabled for {bot_name}")
    
    async def send_notification(self, event: NotificationEvent) -> bool:
        """
        Send a notification for the given event
        
        Args:
            event: NotificationEvent to send
            
        Returns:
            True if notification was sent successfully
        """
        if not self.enabled:
            return False
            
        if not should_send_notification(event, self.min_level):
            self.logger.debug(f"🔇 [NOTIFICATIONS] Skipping notification - below min level {self.min_level.value}")
            return False
        
        try:
            message = format_telegram_message(event)
            success = await self._send_telegram_message(message)
            
            if success:
                self.logger.info(f"📤 [NOTIFICATIONS] Sent {event.event_type.value} notification")
            else:
                self.logger.error(f"❌ [NOTIFICATIONS] Failed to send {event.event_type.value} notification")
                
            return success
            
        except Exception as e:
            self.logger.error(f"❌ [NOTIFICATIONS] Error sending notification: {e}")
            return False
    
    async def _send_telegram_message(self, message: str) -> bool:
        """
        Send message to Telegram chat
        
        Args:
            message: Formatted message to send
            
        Returns:
            True if message was sent successfully
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False
            
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        response_text = await response.text()
                        self.logger.error(f"❌ [NOTIFICATIONS] Telegram API error {response.status}: {response_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ [NOTIFICATIONS] Network error sending to Telegram: {e}")
            return False
    
    # Convenience methods for common events
    async def notify_stop_loss_hit(self, order_id: int, price: float, quantity: int, pnl: float) -> bool:
        """Notify when stop loss is triggered"""
        event = NotificationEvent(
            event_type=EventType.STOP_LOSS_HIT,
            level=NotificationLevel.WARNING,
            title="Stop Loss Triggered",
            message=f"Stop loss order executed for {self.symbol}",
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now(),
            order_id=order_id,
            price=price,
            quantity=quantity,
            pnl=pnl
        )
        return await self.send_notification(event)
    
    async def notify_take_profit_hit(self, order_id: int, price: float, quantity: int, pnl: float) -> bool:
        """Notify when take profit is triggered"""
        event = NotificationEvent(
            event_type=EventType.TAKE_PROFIT_HIT,
            level=NotificationLevel.INFO,
            title="Take Profit Hit",
            message=f"Take profit order executed for {self.symbol}",
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now(),
            order_id=order_id,
            price=price,
            quantity=quantity,
            pnl=pnl
        )
        return await self.send_notification(event)
    
    async def notify_connection_lost(self, error_details: Optional[str] = None) -> bool:
        """Notify when IBKR connection is lost"""
        event = NotificationEvent(
            event_type=EventType.CONNECTION_LOST,
            level=NotificationLevel.CRITICAL,
            title="IBKR Connection Lost",
            message=f"Trading bot {self.bot_name} lost connection to IBKR",
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now(),
            error_details=error_details
        )
        return await self.send_notification(event)
    
    async def notify_connection_restored(self) -> bool:
        """Notify when IBKR connection is restored"""
        event = NotificationEvent(
            event_type=EventType.CONNECTION_RESTORED,
            level=NotificationLevel.INFO,
            title="IBKR Connection Restored",
            message=f"Trading bot {self.bot_name} reconnected to IBKR",
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now()
        )
        return await self.send_notification(event)
    
    async def notify_order_filled(self, order_id: int, price: float, quantity: int, order_type: str) -> bool:
        """Notify when an order is filled"""
        event = NotificationEvent(
            event_type=EventType.ORDER_FILLED,
            level=NotificationLevel.INFO,
            title="Order Filled",
            message=f"{order_type} order filled for {self.symbol}",
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now(),
            order_id=order_id,
            price=price,
            quantity=quantity
        )
        return await self.send_notification(event)
    
    async def notify_bot_started(self) -> bool:
        """Notify when bot starts"""
        event = NotificationEvent(
            event_type=EventType.BOT_STARTED,
            level=NotificationLevel.INFO,
            title="Trading Bot Started",
            message=f"Bot {self.bot_name} started trading {self.symbol} with {self.strategy_name} strategy",
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now()
        )
        return await self.send_notification(event)
    
    async def notify_critical_error(self, error_message: str, error_details: Optional[str] = None) -> bool:
        """Notify when a critical error occurs"""
        event = NotificationEvent(
            event_type=EventType.ERROR_OCCURRED,
            level=NotificationLevel.CRITICAL,
            title="Critical Error",
            message=error_message,
            bot_name=self.bot_name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            timestamp=datetime.now(),
            error_details=error_details
        )
        return await self.send_notification(event)
    
    def is_enabled(self) -> bool:
        """Check if notifications are enabled"""
        return self.enabled
    
    def get_status(self) -> str:
        """Get human-readable notification status"""
        if not self.enabled:
            return "❌ Disabled"
        elif not self.telegram_bot_token or not self.telegram_chat_id:
            return "❌ Missing credentials"
        else:
            return "✅ Enabled"