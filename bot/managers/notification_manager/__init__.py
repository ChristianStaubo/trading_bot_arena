"""
Notification Manager Package

Handles all notification operations for the trading bot.
Sends critical event notifications via Telegram bot.

Structure:
- main.py: Core NotificationManager class and functionality
- types.py: Notification-specific type definitions
- utils.py: Helper functions for message formatting
"""

from .main import NotificationManager

__all__ = ['NotificationManager']