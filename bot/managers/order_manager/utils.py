"""
Order Management Functions for Interactive Brokers

Clean utility functions for placing, canceling, and viewing orders
when you already have an active IB connection.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Literal, TypedDict
from ib_async import IB, Stock, Future, Forex, Contract, Order, MarketOrder, LimitOrder, StopOrder, Trade, BracketOrder, util
import time


# Type definitions for better type safety
OrderAction = Literal["BUY", "SELL"]
ContractType = Literal["Stock", "Future", "Forex"]
OrderStatus = Literal["success", "error"]


class OrderResult(TypedDict):
    """Type-safe result from order placement"""
    status: OrderStatus
    order_id: Optional[int]
    symbol: str
    action: str
    quantity: int
    order_type: str
    order_status: Optional[str]
    message: Optional[str]
    trade_object: Optional[Trade]


class OrderStatusResult(TypedDict):
    """Type-safe result from order status check"""
    status: OrderStatus
    order_id: int
    symbol: str
    action: str
    quantity: int
    order_type: str
    order_status: str
    filled: float
    remaining: float
    avg_fill_price: Optional[float]
    last_fill_price: Optional[float]
    limit_price: Optional[float]
    stop_price: Optional[float]
    time_in_force: str
    account: str
    message: Optional[str]


class CancelResult(TypedDict):
    """Type-safe result from order cancellation"""
    status: OrderStatus
    order_id: int
    message: str


def create_stock_contract(symbol: str, exchange: str = "SMART", currency: str = "USD") -> Stock:
    """Create a stock contract for the given symbol."""
    return Stock(symbol, exchange, currency)


def create_forex_contract(pair: str, exchange: str = "IDEALPRO") -> Forex:
    """Create a forex contract for the given currency pair (e.g. 'EURUSD')."""
    return Forex(pair, exchange=exchange)


def create_future_contract(symbol: str, exchange: str = "CME", currency: str = "USD") -> Future:
    """Create a future contract for the given symbol (e.g., ES)."""
    import datetime as dt
    current_date = dt.datetime.now()
    
    # ES has quarterly contracts (Mar, Jun, Sep, Dec)
    quarterly_months = [3, 6, 9, 12]
    next_quarterly = min([m for m in quarterly_months if m >= current_date.month] + [quarterly_months[0] + 12])
    
    if next_quarterly > 12:
        next_quarterly -= 12
        year = current_date.year + 1
    else:
        year = current_date.year
    
    # Calculate the third Friday of the contract month
    import calendar
    third_friday = 15
    while calendar.weekday(year, next_quarterly, third_friday) != 4:  # 4 = Friday
        third_friday += 1
        if third_friday > 21:
            third_friday = 19
            break
    
    contract_month = f"{year}{next_quarterly:02d}{third_friday:02d}"
    
    return Future(
        symbol=symbol,
        lastTradeDateOrContractMonth=contract_month,
        exchange=exchange,
        currency=currency,
        multiplier="50"  # ES multiplier
    )


def place_market_order(
    ib: IB,
    symbol: str,
    action: OrderAction,
    quantity: int,
    contract_type: ContractType = "Stock",
    exchange: str = "SMART",
    currency: str = "USD"
) -> OrderResult:
    """
    Place a market order.
    
    Args:
        ib: Connected IB instance
        symbol: Symbol to trade
        action: "BUY" or "SELL"
        quantity: Number of shares/contracts
        contract_type: "Stock", "Future", or "Forex"
        exchange: Exchange name
        currency: Currency (for forex, this is the quote currency)
    
    Returns:
        OrderResult: Type-safe order details and status
    """
    print(f"📋 Placing {action} market order for {quantity} {symbol}...")
    
    try:
        # Create contract
        contract: Contract
        if contract_type == "Stock":
            contract = create_stock_contract(symbol, exchange, currency)
        elif contract_type == "Future":
            contract = create_future_contract(symbol, exchange, currency)
        elif contract_type == "Forex":
            contract = create_forex_contract(symbol, exchange)
        else:
            return OrderResult(
                status="error",
                order_id=None,
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type="MKT",
                order_status=None,
                message=f"Unsupported contract type: {contract_type}",
                trade_object=None
            )
        
        # Qualify the contract
        contracts = ib.qualifyContracts(contract)
        if not contracts:
            return OrderResult(
                status="error",
                order_id=None,
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type="MKT",
                order_status=None,
                message=f"Could not qualify contract for {symbol}",
                trade_object=None
            )
        
        qualified_contract = contracts[0]
        print(f"✅ Contract qualified: {qualified_contract}")
        
        # Create market order
        order = MarketOrder(action, quantity)
        
        # Place order
        trade = ib.placeOrder(qualified_contract, order)
        
        # Wait a moment for order to be processed
        ib.sleep(1)
        
        result: OrderResult = {
            "status": "success",
            "order_id": trade.order.orderId,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_type": "MKT",
            "order_status": trade.orderStatus.status,
            "message": None,
            "trade_object": trade
        }
        
        print(f"✅ Market order placed successfully!")
        print(f"   📋 Order ID: {result['order_id']}")
        print(f"   📊 Status: {result['order_status']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error placing market order: {e}")
        return OrderResult(
            status="error",
            order_id=None,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type="MKT",
            order_status=None,
            message=str(e),
            trade_object=None
        )


def place_limit_order(
    ib: IB,
    symbol: str,
    action: OrderAction,
    quantity: int,
    limit_price: float,
    contract_type: ContractType = "Stock",
    exchange: str = "SMART",
    currency: str = "USD"
) -> Trade:
    """
    Place a limit order.
    
    Args:
        ib: Connected IB instance
        symbol: Symbol to trade
        action: "BUY" or "SELL"
        quantity: Number of shares/contracts
        limit_price: Limit price
        contract_type: "Stock", "Future", or "Forex"
        exchange: Exchange name
        currency: Currency (for forex, this is the quote currency)
    
    Returns:
        OrderResult: Type-safe order details and status
    """
    print(f"📋 Placing {action} limit order for {quantity} {symbol} at {limit_price}...")
    
    try:
        # Create contract
        contract: Contract
        if contract_type == "Stock":
            contract = create_stock_contract(symbol, exchange, currency)
        elif contract_type == "Future":
            contract = create_future_contract(symbol, exchange, currency)
        elif contract_type == "Forex":
            contract = create_forex_contract(symbol, exchange)
        else:
            raise ValueError(f"Unsupported contract type: {contract_type}")
        
        # Qualify the contract
        contracts = ib.qualifyContracts(contract)
        if not contracts:
            raise ValueError(f"Could not qualify contract for {symbol}")
        
        qualified_contract = contracts[0]
        print(f"✅ Contract qualified: {qualified_contract}")
        
        # Create limit order
        order = LimitOrder(action, quantity, limit_price)
        
        # Place order
        trade = ib.placeOrder(qualified_contract, order)
        
        # Wait a moment for order to be processed
        ib.sleep(1)
        
        return trade

        
        
        
        
    except Exception as e:
        print(f"❌ Error placing limit order: {e}")
        return OrderResult(
            status="error",
            order_id=None,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type="LMT",
            order_status=None,
            message=str(e),
            trade_object=None
        )


def place_stop_order(
    ib: IB,
    symbol: str,
    action: OrderAction,
    quantity: int,
    stop_price: float,
    contract_type: ContractType = "Stock",
    exchange: str = "SMART",
    currency: str = "USD"
) -> OrderResult:
    """
    Place a stop order.
    
    Args:
        ib: Connected IB instance
        symbol: Symbol to trade
        action: "BUY" or "SELL"
        quantity: Number of shares/contracts
        stop_price: Stop price
        contract_type: "Stock", "Future", or "Forex"
        exchange: Exchange name
        currency: Currency (for forex, this is the quote currency)
    
    Returns:
        OrderResult: Type-safe order details and status
    """
    print(f"📋 Placing {action} stop order for {quantity} {symbol} at {stop_price}...")
    
    try:
        # Create contract
        contract: Contract
        if contract_type == "Stock":
            contract = create_stock_contract(symbol, exchange, currency)
        elif contract_type == "Future":
            contract = create_future_contract(symbol, exchange, currency)
        elif contract_type == "Forex":
            contract = create_forex_contract(symbol, exchange)
        else:
            return OrderResult(
                status="error",
                order_id=None,
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type="STP",
                order_status=None,
                message=f"Unsupported contract type: {contract_type}",
                trade_object=None
            )
        
        # Qualify the contract
        contracts = ib.qualifyContracts(contract)
        if not contracts:
            return OrderResult(
                status="error",
                order_id=None,
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type="STP",
                order_status=None,
                message=f"Could not qualify contract for {symbol}",
                trade_object=None
            )
        
        qualified_contract = contracts[0]
        print(f"✅ Contract qualified: {qualified_contract}")
        
        # Create stop order
        order = StopOrder(action, quantity, stop_price)
        
        # Place order
        trade = ib.placeOrder(qualified_contract, order)
        
        # Wait a moment for order to be processed
        ib.sleep(1)
        
        result: OrderResult = {
            "status": "success",
            "order_id": trade.order.orderId,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_type": "STP",
            "order_status": trade.orderStatus.status,
            "message": None,
            "trade_object": trade
        }
        
        print(f"✅ Stop order placed successfully!")
        print(f"   📋 Order ID: {result['order_id']}")
        print(f"   📊 Status: {result['order_status']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error placing stop order: {e}")
        return OrderResult(
            status="error",
            order_id=None,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type="STP",
            order_status=None,
            message=str(e),
            trade_object=None
        )


def place_bracket_order(
    ib: IB,
    symbol: str,
    action: OrderAction,
    quantity: int,
    limit_price: float,
    take_profit_price: float,
    stop_loss_price: float,
    contract_type: ContractType = "Stock",
    exchange: str = "SMART",
    currency: str = "USD"
) -> List[Trade]:
    """
    Place a bracket order (OCO) with entry, take profit, and stop loss using IBKR's built-in bracket order.
    
    Args:
        ib: Connected IB instance
        symbol: Symbol to trade
        action: "BUY" or "SELL"
        quantity: Number of shares/contracts
        limit_price: Entry limit price
        take_profit_price: Take profit limit price
        stop_loss_price: Stop loss trigger price
        contract_type: "Stock", "Future", or "Forex"
        exchange: Exchange name
        currency: Currency
    
    Returns:
        List of Trade objects [parent, takeProfit, stopLoss]
    """
    print(f"📋 Placing bracket order for {quantity} {symbol}...")
    print(f"   Entry: ${limit_price:.2f}, TP: ${take_profit_price:.2f}, SL: ${stop_loss_price:.2f}")
    
    try:
        # Create contract
        contract: Contract
        if contract_type == "Stock":
            contract = create_stock_contract(symbol, exchange, currency)
        elif contract_type == "Future":
            contract = create_future_contract(symbol, exchange, currency)
        elif contract_type == "Forex":
            contract = create_forex_contract(symbol, exchange)
        else:
            raise ValueError(f"Unsupported contract type: {contract_type}")
        
        # Qualify the contract
        contracts = ib.qualifyContracts(contract)
        if not contracts:
            raise ValueError(f"Could not qualify contract for {symbol}")
        
        qualified_contract = contracts[0]
        print(f"✅ Contract qualified: {qualified_contract}")
        
        # Create bracket order using ib_async's built-in method
        bracket = ib.bracketOrder(
            action=action,
            quantity=quantity,
            limitPrice=limit_price,
            takeProfitPrice=take_profit_price,
            stopLossPrice=stop_loss_price
        )
        
        # Place all orders from the bracket
        trades: List[Trade] = []
        for order in bracket:
            trade = ib.placeOrder(qualified_contract, order)
            trades.append(trade)
        
        # Wait for orders to be processed
        ib.sleep(1)
        
        print(f"✅ Bracket order placed successfully!")
        print(f"   Parent Order ID: {trades[0].order.orderId}")
        print(f"   Take Profit Order ID: {trades[1].order.orderId}")
        print(f"   Stop Loss Order ID: {trades[2].order.orderId}")
        
        return trades
        
    except Exception as e:
        print(f"❌ Error placing bracket order for {symbol}: {e}")
        raise e


def cancel_order(ib: IB, order_id: int) -> CancelResult:
    """
    Cancel an order by order ID.
    
    Args:
        ib: Connected IB instance
        order_id: Order ID to cancel
    
    Returns:
        CancelResult: Type-safe cancellation result
    """
    print(f"🚫 Cancelling order {order_id}...")
    
    try:
        # Find the trade object for this order
        trade: Optional[Trade] = None
        for t in ib.trades():
            if t.order.orderId == order_id:
                trade = t
                break
        
        if not trade:
            return CancelResult(
                status="error",
                order_id=order_id,
                message=f"Order {order_id} not found"
            )
        
        # Cancel the order
        ib.cancelOrder(trade.order)
        
        # Wait a moment for cancellation to be processed
        ib.sleep(1)
        
        result: CancelResult = {
            "status": "success",
            "order_id": order_id,
            "message": f"Order {order_id} cancellation requested"
        }
        
        print(f"✅ Order {order_id} cancellation requested!")
        
        return result
        
    except Exception as e:
        print(f"❌ Error cancelling order {order_id}: {e}")
        return CancelResult(
            status="error",
            order_id=order_id,
            message=str(e)
        )


def get_open_orders(ib: IB) -> pd.DataFrame:
    """
    Get all open orders.
    
    Args:
        ib: Connected IB instance
    
    Returns:
        pd.DataFrame: Open orders data
    """
    print("📋 Fetching open orders...")
    
    try:
        # Get all open orders
        open_orders = ib.openTrades()
        
        if not open_orders:
            print("📋 No open orders found")
            return pd.DataFrame()
        
        # Convert to list of dictionaries
        orders_data = []
        for trade in open_orders:
            order_data = {
                "order_id": trade.order.orderId,
                "symbol": trade.contract.symbol,
                "action": trade.order.action,
                "quantity": trade.order.totalQuantity,
                "order_type": trade.order.orderType,
                "status": trade.orderStatus.status,
                "limit_price": getattr(trade.order, 'lmtPrice', None),
                "stop_price": getattr(trade.order, 'auxPrice', None),
                "filled": trade.orderStatus.filled,
                "remaining": trade.orderStatus.remaining,
                "avg_fill_price": trade.orderStatus.avgFillPrice,
                "last_fill_price": trade.orderStatus.lastFillPrice,
                "parent_id": trade.order.parentId,
                "account": trade.order.account,
                "exchange": trade.contract.exchange,
                "currency": trade.contract.currency
            }
            orders_data.append(order_data)
        
        df = pd.DataFrame(orders_data)
        
        print(f"📋 Found {len(df)} open orders")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching open orders: {e}")
        return pd.DataFrame()


def get_order_status(ib: IB, order_id: int) -> OrderStatusResult:
    """
    Get status of a specific order.
    
    Args:
        ib: Connected IB instance
        order_id: Order ID to check
    
    Returns:
        OrderStatusResult: Type-safe order status details
    """
    print(f"🔍 Checking status of order {order_id}...")
    
    try:
        # Find the trade object for this order
        trade: Optional[Trade] = None
        for t in ib.trades():
            if t.order.orderId == order_id:
                trade = t
                break
        
        if not trade:
            return OrderStatusResult(
                status="error",
                order_id=order_id,
                symbol="",
                action="",
                quantity=0,
                order_type="",
                order_status="",
                filled=0.0,
                remaining=0.0,
                avg_fill_price=None,
                last_fill_price=None,
                limit_price=None,
                stop_price=None,
                time_in_force="",
                account="",
                message=f"Order {order_id} not found"
            )
        
        result: OrderStatusResult = {
            "status": "success",
            "order_id": order_id,
            "symbol": trade.contract.symbol,
            "action": trade.order.action,
            "quantity": trade.order.totalQuantity,
            "order_type": trade.order.orderType,
            "order_status": trade.orderStatus.status,
            "filled": trade.orderStatus.filled,
            "remaining": trade.orderStatus.remaining,
            "avg_fill_price": trade.orderStatus.avgFillPrice,
            "last_fill_price": trade.orderStatus.lastFillPrice,
            "limit_price": getattr(trade.order, 'lmtPrice', None),
            "stop_price": getattr(trade.order, 'auxPrice', None),
            "time_in_force": trade.order.tif,
            "account": trade.order.account,
            "message": None
        }
        
        print(f"✅ Order {order_id} found:")
        print(f"   📊 Status: {result['order_status']}")
        print(f"   📋 {result['action']} {result['quantity']} {result['symbol']}")
        print(f"   💰 Filled: {result['filled']}, Remaining: {result['remaining']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error checking order {order_id}: {e}")
        return OrderStatusResult(
            status="error",
            order_id=order_id,
            symbol="",
            action="",
            quantity=0,
            order_type="",
            order_status="",
            filled=0.0,
            remaining=0.0,
            avg_fill_price=None,
            last_fill_price=None,
            limit_price=None,
            stop_price=None,
            time_in_force="",
            account="",
            message=str(e)
        )


def get_trades_history(ib: IB, symbol: str = None) -> pd.DataFrame:
    """
    Get historical trades (filled orders).
    
    Args:
        ib: Connected IB instance
        symbol: Optional symbol filter
    
    Returns:
        pd.DataFrame: Historical trades data
    """
    print(f"📈 Fetching trades history{' for ' + symbol if symbol else ''}...")
    
    try:
        # Get all trades
        all_trades = ib.trades()
        
        if not all_trades:
            print("📈 No trades found")
            return pd.DataFrame()
        
        # Filter by symbol if provided
        if symbol:
            all_trades = [t for t in all_trades if t.contract.symbol == symbol]
        
        # Convert to list of dictionaries
        trades_data = []
        for trade in all_trades:
            if trade.orderStatus.status in ["Filled", "Cancelled"]:  # Only show completed trades
                trade_data = {
                    "order_id": trade.order.orderId,
                    "symbol": trade.contract.symbol,
                    "action": trade.order.action,
                    "quantity": trade.order.totalQuantity,
                    "order_type": trade.order.orderType,
                    "status": trade.orderStatus.status,
                    "filled": trade.orderStatus.filled,
                    "avg_fill_price": trade.orderStatus.avgFillPrice,
                    "commission": getattr(trade.orderStatus, 'commission', None),
                    "time": trade.log[-1].time if trade.log else None,
                    "account": trade.order.account,
                    "exchange": trade.contract.exchange,
                    "currency": trade.contract.currency
                }
                trades_data.append(trade_data)
        
        df = pd.DataFrame(trades_data)
        
        if not df.empty:
            df = df.sort_values('time', ascending=False).reset_index(drop=True)
        
        print(f"📈 Found {len(df)} completed trades")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching trades history: {e}")
        return pd.DataFrame()


def get_positions(ib: IB) -> pd.DataFrame:
    """
    Get current positions.
    
    Args:
        ib: Connected IB instance
    
    Returns:
        pd.DataFrame: Current positions data
    """
    print("💼 Fetching current positions...")
    
    try:
        # Get all positions
        positions = ib.positions()
        
        if not positions:
            print("💼 No positions found")
            return pd.DataFrame()
        
        # Convert to list of dictionaries
        positions_data = []
        for position in positions:
            position_data = {
                "symbol": position.contract.symbol,
                "position": position.position,  # Number of shares/units held
                "avg_cost": position.avgCost,   # Average cost per share
                "account": position.account,
                "exchange": position.contract.exchange,
                "currency": position.contract.currency,
                "contract_type": position.contract.secType
            }
            positions_data.append(position_data)
        
        df = pd.DataFrame(positions_data)
        
        print(f"💼 Found {len(df)} positions")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        return pd.DataFrame()


# Order type convenience functions
ORDER_TYPES = {
    "market": "MKT",
    "limit": "LMT", 
    "stop": "STP",
    "stop_limit": "STP LMT"
}

ACTIONS = {
    "buy": "BUY",
    "sell": "SELL"
} 