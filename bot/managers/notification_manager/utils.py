"""
Notification Manager Utilities

Helper functions for message formatting and notification processing.
"""

from typing import Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv
from .types import NotificationEvent, NotificationLevel, EventType, NotificationSettings


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram markdown
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Telegram markdown
    """
    # Characters that need escaping in Telegram markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_telegram_message(event: NotificationEvent) -> str:
    """
    Format a notification event into a Telegram message
    
    Args:
        event: NotificationEvent to format
        
    Returns:
        Formatted message string for Telegram
    """
    # Emoji mapping for different event types and levels
    level_emojis: Dict[NotificationLevel, str] = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.WARNING: "⚠️", 
        NotificationLevel.ERROR: "❌",
        NotificationLevel.CRITICAL: "🚨"
    }
    
    event_emojis: Dict[EventType, str] = {
        EventType.TRADE_SIGNAL: "📈",
        EventType.ORDER_PLACED: "📋",
        EventType.ORDER_FILLED: "✅",
        EventType.ORDER_CANCELLED: "❌",
        EventType.STOP_LOSS_HIT: "🛑",
        EventType.TAKE_PROFIT_HIT: "🎯",
        EventType.CONNECTION_LOST: "📡",
        EventType.CONNECTION_RESTORED: "🔄",
        EventType.BOT_STARTED: "🚀",
        EventType.BOT_STOPPED: "⏸️",
        EventType.ERROR_OCCURRED: "💥"
    }
    
    # Build message
    level_emoji = level_emojis.get(event.level, "📢")
    event_emoji = event_emojis.get(event.event_type, "📊")
    
    lines = [
        f"{level_emoji} {event_emoji} **{event.title}**",
        "",
        f"**Bot:** {event.bot_name}",
        f"**Symbol:** {event.symbol}",
        f"**Strategy:** {event.strategy_name}",
        f"**Time:** {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    # Add optional fields if present
    if event.order_id:
        lines.append(f"**Order ID:** {event.order_id}")
    
    if event.price:
        lines.append(f"**Price:** ${event.price:,.2f}")
    
    if event.quantity:
        lines.append(f"**Quantity:** {event.quantity}")
    
    if event.pnl is not None:
        pnl_sign = "+" if event.pnl >= 0 else ""
        lines.append(f"**P&L:** {pnl_sign}${event.pnl:,.2f}")
    
    if event.error_details:
        lines.extend(["", f"**Error:** {escape_markdown(event.error_details)}"])
    
    # Add main message
    lines.extend(["", escape_markdown(event.message)])
    
    return "\n".join(lines)


def get_notification_settings() -> NotificationSettings:
    """
    Get notification settings from environment variables
    
    Returns:
        NotificationSettings with type-safe configuration
    """
    # Load environment variables
    load_dotenv()
    
    return NotificationSettings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        enabled=os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true",
        min_level=NotificationLevel(os.getenv("NOTIFICATION_MIN_LEVEL", "info"))
    )


def should_send_notification(event: NotificationEvent, min_level: NotificationLevel) -> bool:
    """
    Determine if a notification should be sent based on level filtering
    
    Args:
        event: NotificationEvent to check
        min_level: Minimum notification level to send
        
    Returns:
        True if notification should be sent
    """
    level_priority: Dict[NotificationLevel, int] = {
        NotificationLevel.INFO: 1,
        NotificationLevel.WARNING: 2,
        NotificationLevel.ERROR: 3,
        NotificationLevel.CRITICAL: 4
    }
    
    return level_priority[event.level] >= level_priority[min_level]