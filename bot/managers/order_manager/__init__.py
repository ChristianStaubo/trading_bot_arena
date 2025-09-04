"""
Order Manager Package

Handles order execution and position management for IBKR trading.

Structure:
- main.py: Core OrderManager class and functionality
- types.py: Type definitions for orders and positions
- utils.py: Helper functions and utilities
"""

from .main import OrderManager
from .types import OrderInfo, Position

__all__ = ['OrderManager', 'OrderInfo', 'Position'] 