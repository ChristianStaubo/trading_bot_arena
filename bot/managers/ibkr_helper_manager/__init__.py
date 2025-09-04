"""
IBKR Helper Manager Package

Handles all IBKR-specific operations including connection management,
contract creation, and real-time data subscriptions.

Structure:
- main.py: Core IbkrHelperManager class and functionality
- types.py: Type definitions for IBKR operations and data structures
- utils.py: Helper functions and utilities for contract creation and validation
"""

from .main import IbkrHelperManager
from .types import (
    DurationStr, BarSizeSetting, WhatToShow, AssetType, ConnectionStatus,
    IbkrConnectionConfig, HistoricalDataRequest, ContractConfig, 
    BarData, MarketDataConfig, IbkrManagerStatus
)

__all__ = [
    'IbkrHelperManager',
    'DurationStr', 'BarSizeSetting', 'WhatToShow', 'AssetType', 'ConnectionStatus',
    'IbkrConnectionConfig', 'HistoricalDataRequest', 'ContractConfig',
    'BarData', 'MarketDataConfig', 'IbkrManagerStatus'
] 