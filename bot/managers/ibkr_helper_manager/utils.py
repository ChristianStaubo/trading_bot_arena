"""
IBKR Helper Manager Utilities

Helper functions for IBKR contract creation, data conversion, 
and other utility operations.
"""

from typing import Optional, Dict, Any, get_args
from ib_async import Contract, Stock, Future, Forex, ContFuture, Ticker
from .types import DurationStr, BarSizeSetting, WhatToShow


def create_contract_by_type(symbol: str, asset_type: str, exchange: str) -> Optional[Contract]:
    """
    Create an IBKR contract based on asset type
    
    Args:
        symbol: Trading symbol (e.g., 'EURUSD', 'ES', 'AAPL')
        asset_type: 'forex', 'futures', or 'stocks'
        exchange: Exchange name
        
    Returns:
        IBKR Contract object or None if failed
    """
    try:
        asset_type_lower = asset_type.lower()
        
        if asset_type_lower == "forex":
            return Forex(symbol)
        elif asset_type_lower == "futures":
            if symbol == "ES":
                # Use continuous future for ES - automatically handles front month
                return ContFuture(symbol='ES', exchange=exchange)
            else:
                return Future(symbol=symbol, exchange=exchange)
        elif asset_type_lower == "stocks":
            return Stock(symbol, exchange, "USD")
        else:
            raise ValueError(f"Unknown asset type: {asset_type} (supported: forex, futures, stocks)")
            
    except Exception as e:
        print(f"❌ Error creating contract for {symbol}: {e}")
        return None


def validate_bar_size(bar_size: str) -> bool:
    """
    Validate if bar size is supported by IBKR

    Args:
        bar_size: Bar size string

    Returns:
        True if valid, False otherwise
    """
    return bar_size in get_args(BarSizeSetting)

def validate_duration_str(duration: str) -> bool:
    """
    Validate if duration string is properly formatted
    
    Args:
        duration: Duration string (e.g., '60 S', '30 D', '13 W')
        
    Returns:
        True if valid format, False otherwise
    """
    import re
    # Pattern: number + space + unit (S, D, W, M, Y)
    pattern = r'^\d+\s[SDWMY]$'
    return bool(re.match(pattern, duration))


def validate_what_to_show(what_to_show: str) -> bool:
    """
    Validate if whatToShow parameter is supported
    
    Args:
        what_to_show: What to show parameter
        
    Returns:
        True if valid, False otherwise
    """
    return what_to_show in get_args(WhatToShow)



def format_symbol_for_logging(symbol: str, contract: Contract = None) -> str:
    """
    Format symbol with contract info for logging
    
    Args:
        symbol: Trading symbol
        contract: IBKR contract (optional)
        
    Returns:
        Formatted string for logging
    """
    if contract and hasattr(contract, 'conId'):
        return f"{symbol} (ConId: {contract.conId})"
    return symbol


def get_current_price(ticker: Ticker) -> Optional[float]:
    """
    Get the most appropriate current price from IBKR ticker
    
    Args:
        ticker: IBKR ticker object
        
    Returns:
        Current price (last, or midpoint of bid/ask, or bid, or ask)
    """
    # Priority: last trade, then midpoint, then bid, then ask
    if ticker.last and ticker.last > 0:
        return float(ticker.last)
    
    if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
        return (float(ticker.bid) + float(ticker.ask)) / 2
    
    if ticker.bid and ticker.bid > 0:
        return float(ticker.bid)
        
    if ticker.ask and ticker.ask > 0:
        return float(ticker.ask)
    
    return None



def calculate_price_distance(current_price: float, entry_price: float, 
                           distance_type: str = 'absolute') -> float:
    """
    Calculate distance between current price and entry price
    
    Args:
        current_price: Current market price
        entry_price: Entry price of position
        distance_type: 'absolute', 'percentage', or 'ticks'
        
    Returns:
        Distance value
    """
    if distance_type == 'absolute':
        return abs(current_price - entry_price)
    elif distance_type == 'percentage':
        return abs((current_price - entry_price) / entry_price) * 100
    elif distance_type == 'ticks':
        # For now, assume 1 tick = 0.01 (can be customized later)
        return abs(current_price - entry_price) / 0.01
    else:
        raise ValueError(f"Unknown distance_type: {distance_type}")


def should_cancel_order_by_distance(current_price: float, entry_price: float,
                                  max_distance: float, distance_type: str = 'absolute') -> bool:
    """
    Check if order should be canceled based on price movement
    
    Args:
        current_price: Current market price
        entry_price: Entry price of order
        max_distance: Maximum allowed distance
        distance_type: 'absolute', 'percentage', or 'ticks'
        
    Returns:
        True if order should be canceled
    """
    distance = calculate_price_distance(current_price, entry_price, distance_type)
    return distance > max_distance


def should_cancel_order_by_ticker(ticker, entry_price: float, max_distance: float, 
                                distance_type: str = 'absolute') -> bool:
    """
    Check if order should be canceled based on ticker price movement
    
    Args:
        ticker: IBKR ticker object
        entry_price: Entry price of order
        max_distance: Maximum allowed distance
        distance_type: 'absolute', 'percentage', or 'ticks'
        
    Returns:
        True if order should be canceled
    """
    current_price = get_current_price(ticker)
    if current_price is None:
        return False
    
    return should_cancel_order_by_distance(current_price, entry_price, max_distance, distance_type) 