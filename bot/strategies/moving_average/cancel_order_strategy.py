"""
Order Cancellation Strategy for Moving Average Strategy

Takes ib_async.Ticker, ib_async.Trade, and datetime to determine cancellation.
Clean, type-safe approach using native IBKR objects.
"""

from datetime import datetime
from ib_async import Ticker, Trade
from typing import Optional


def should_cancel_order(ticker: Ticker, trade: Trade, order_time: datetime) -> bool:
    """
    Determine if order should be canceled based on real-time data and trade status.
    
    Args:
        ticker: ib_async.Ticker with real-time market data
        trade: ib_async.Trade object from IBKR
        order_time: datetime when order was placed
    
    Returns:
        bool: True if order should be canceled, False otherwise
    """
    
    # Check if 5 minutes have elapsed
    elapsed_seconds = (datetime.now() - order_time).total_seconds()
    if elapsed_seconds < 300:
        return False  # Not enough time elapsed yet
    
    # Check if order is still pending (not filled)
    order_status = trade.orderStatus.status
    remaining = trade.orderStatus.remaining
    
    # Only cancel if order is still pending and not filled
    if order_status in ["Submitted", "PreSubmitted", "PendingSubmit"] and remaining > 0:
        print(f"⏰ MA Strategy: Canceling order {trade.order.orderId}: "
              f"{elapsed_seconds:.1f}s elapsed, still pending ({order_status})")
        return True
    else:
        print(f"✅ MA Strategy: Order {trade.order.orderId} status: {order_status} "
              f"(filled: {trade.orderStatus.filled}, remaining: {remaining})")
        return False  # Order was filled or already cancelled


def _get_current_price(ticker: Ticker) -> Optional[float]:
    """
    Get best current price from ticker
    
    Args:
        ticker: IBKR ticker object with market data
        
    Returns:
        Current price if available, None otherwise
    """
    if ticker.last and ticker.last > 0:
        return float(ticker.last)
    if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
        return (float(ticker.bid) + float(ticker.ask)) / 2
    if ticker.bid and ticker.bid > 0:
        return float(ticker.bid)
    if ticker.ask and ticker.ask > 0:
        return float(ticker.ask)
    return None