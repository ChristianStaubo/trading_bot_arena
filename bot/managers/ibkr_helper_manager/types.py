"""
IBKR Helper Manager Types

Type definitions for IBKR-specific operations to improve type safety
and prevent common mistakes like using "5 min" instead of "5 mins".
"""

from typing import Literal, Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


# Duration string for historical data requests
# Examples: '60 S', '30 D', '13 W', '6 M', '10 Y'
DurationStr = Literal[
    # Seconds
    '60 S', '120 S', '300 S', '600 S', '1800 S', '3600 S',
    # Days  
    '1 D', '2 D', '3 D', '4 D', '5 D', '10 D', '30 D',
    # Weeks
    '1 W', '2 W', '4 W', '13 W', '26 W', '52 W',
    # Months
    '1 M', '2 M', '3 M', '6 M', '12 M',
    # Years
    '1 Y', '2 Y', '5 Y', '10 Y'
]

# Bar size setting - time period of one bar
BarSizeSetting = Literal[
    # Seconds
    '1 secs', '5 secs', '10 secs', '15 secs', '30 secs',
    # Minutes
    '1 min', '2 mins', '3 mins', '5 mins', '10 mins', '15 mins',
    '20 mins', '30 mins',
    # Hours
    '1 hour', '2 hours', '3 hours', '4 hours', '8 hours',
    # Days/Weeks/Months
    '1 day', '1 week', '1 month'
]

# What to show - source for constructing bars
WhatToShow = Literal[
    'TRADES', 'MIDPOINT', 'BID', 'ASK', 'BID_ASK',
    'ADJUSTED_LAST', 'HISTORICAL_VOLATILITY',
    'OPTION_IMPLIED_VOLATILITY', 'REBATE_RATE', 'FEE_RATE',
    'YIELD_BID', 'YIELD_ASK', 'YIELD_BID_ASK', 'YIELD_LAST'
]

# Asset types supported by the manager
AssetType = Literal['forex', 'futures', 'stocks']

# Connection status
ConnectionStatus = Literal['connected', 'disconnected', 'connecting', 'error']


@dataclass
class IbkrConnectionConfig:
    """Configuration for IBKR connection"""
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1


@dataclass
class HistoricalDataRequest:
    """Configuration for historical data requests"""
    duration_str: DurationStr
    bar_size_setting: BarSizeSetting
    what_to_show: WhatToShow = 'TRADES'
    use_rth: bool = False  # Include after-hours data
    format_date: int = 1
    keep_up_to_date: bool = True


@dataclass
class ContractConfig:
    """Configuration for creating contracts"""
    symbol: str
    asset_type: AssetType
    exchange: str
    currency: str = "USD"


@dataclass
class BarData:
    """Standardized bar data structure"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class MarketDataConfig:
    """Configuration for market data subscriptions"""
    symbol: str
    generic_tick_list: str = ''  # Empty for basic data
    snapshot: bool = False
    regulatory_snapshot: bool = False
    mkt_data_options: Optional[list] = None


@dataclass
class IbkrManagerStatus:
    """Status information for IBKR manager"""
    connection_status: ConnectionStatus
    active_contracts: Dict[str, str]  # symbol -> contract_id mapping
    active_subscriptions: List[str]   # list of symbols with active bar data feeds
    active_ticker_subscriptions: List[str]  # list of symbols with active ticker feeds
    last_update: Optional[datetime] = None 