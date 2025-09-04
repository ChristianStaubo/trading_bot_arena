"""
Trading Bot Managers Package

This package contains all the specialized manager classes that handle
specific concerns for the trading bot, promoting clean separation of concerns.

Available Managers:
- IbkrHelperManager: Handles all IBKR-specific operations and connections
- LoggingManager: Centralized logging management and setup
- TradeManager: Strategy execution and trade decision management
"""

from .ibkr_helper_manager import IbkrHelperManager
from .logging_manager import LoggingManager
from .trade_decision_manager import TradeDecisionManager
from .order_manager.main import OrderManager

__all__ = ['IbkrHelperManager', 'LoggingManager', 'TradeDecisionManager', 'OrderManager'] 