"""
Data and Strategy Manager Package

Handles both data fetching operations and strategy loading for the trading bot.
This manager centralizes all data-related and strategy-related initialization tasks.

Structure:
- main.py: Core DataAndStrategyManager class and functionality
"""

from .main import DataAndStrategyManager

__all__ = ['DataAndStrategyManager']