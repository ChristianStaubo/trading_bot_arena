import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from typing import Dict, Optional, List, Callable, Any, TypedDict, TYPE_CHECKING, Set, Union

if TYPE_CHECKING:
    from managers.notification_manager import NotificationManager
from datetime import datetime, timedelta
from dataclasses import dataclass
from ib_async import IB, Contract, Trade, Ticker
from managers.trade_decision_manager import CandleResult, TradeSignal
from managers.order_manager.types import Position
from managers.order_manager.utils import (
    place_market_order, place_limit_order, place_stop_order, place_bracket_order, cancel_order, 
    get_order_status, OrderResult, OrderStatusResult, 
    CancelResult, OrderAction, ContractType
)
import asyncio
from logging import Logger

# Import cancel strategy types
from lib.types.cancel_strategy import CancelStrategyFunction

# Import manager types for proper type hinting
if TYPE_CHECKING:
    from managers.ibkr_helper_manager import IbkrHelperManager
    from managers.api_manager import ApiManager

class StrategyOrdersDebugInfo(TypedDict):
    """Type-safe structure for strategy order debug information"""
    strategy_name: str
    symbol: str
    local_trade_count: int
    ibkr_trade_count: Union[int, str]  # int when connected, "N/A" when not
    local_order_ids: List[int]
    in_sync: Union[bool, str]  # bool when comparable, "Unknown" when IBKR unavailable
    strategy_tag_prefix: str
    error: Optional[str]

@dataclass
class PlaceOrderResult:
    parent_order_id: int
    tp_order_id: int
    sl_order_id: int
    trades: List[Trade]
    entry_price: float
    take_profit: float
    stop_loss: float






class OrderManager:
    """
    Manages order execution and position tracking for IBKR trading.
    
    Handles:
    - OCO order placement with TP/SL
    - Order state tracking and monitoring
    - Position management
    - Configurable order management rules
    - Integration with existing order_management.py functions
    """
    
    def __init__(self, 
                 ib: IB, 
                 get_contract: Callable[[str], Optional[Contract]],
                 max_concurrent_trades: int = 1,
                 logger: Logger = None,
                 default_quantity: int = 2,
                 ibkr_manager: Optional['IbkrHelperManager'] = None,
                 api_manager: Optional['ApiManager'] = None,
                 strategy_name: str = "unknown",
                 symbol: str = "UNKNOWN",
                 notification_manager: Optional['NotificationManager'] = None):
        """
        Initialize OrderManager
        
        Args:
            ib: Connected IB instance
            get_contract: Function to get contract for a symbol
            max_concurrent_trades: Maximum number of concurrent trades allowed
            logger: Logger instance
            default_quantity: Default order quantity
            ibkr_manager: IBKR helper manager for ticker subscriptions
            api_manager: API manager for posting trade events
            strategy_name: Name of the trading strategy
            symbol: Trading symbol for this manager
            notification_manager: Notification manager for sending alerts
        """
        self.ib: IB = ib
        self.get_contract: Callable[[str], Optional[Contract]] = get_contract
        self.max_concurrent_trades: int = max_concurrent_trades
        self.default_quantity: int = default_quantity
        self.logger: Logger = logger
        self.ibkr_manager: Optional['IbkrHelperManager'] = ibkr_manager
        self.api_manager: Optional['ApiManager'] = api_manager
        self.notification_manager: Optional['NotificationManager'] = notification_manager
        self.strategy_name: str = strategy_name
        self.symbol: str = symbol
        
        # Order and position tracking
        self.active_orders: Dict[str, List[Trade]] = {}  # symbol -> list of Trade objects
        self.positions: Dict[str, Position] = {}  # symbol -> position
        
        # Track last price for each symbol
        self.last_prices: Dict[str, float] = {}
        
        # Order monitoring state for cancel strategies
        self.monitoring_orders: Dict[int, datetime] = {}  # order_id -> order_time
        self.monitoring_active_orders: Dict[int, Trade] = {}  # order_id -> Trade object for monitoring
        self.cancel_strategy_function: Optional[CancelStrategyFunction] = None
        self._order_lock: Optional[asyncio.Lock] = None  # Will be initialized when needed
    
    async def place_order(self, result: CandleResult) -> PlaceOrderResult:
        """
        Place a bracket order (OCO) based on trade signal using IBKR Trade events
        
        Args:
            result: CandleResult with trade_signal containing entry, TP, SL levels
            
        Returns:
            PlaceOrderResult with order details
            
        Raises:
            RuntimeError: If contract not found, position already exists, or trade limits reached
            Exception: If order placement fails for any reason
        """
        # Store current symbol for tick size calculation
        self._current_symbol = result.symbol
        
        # Get contract for symbol
        contract = self.get_contract(result.symbol)
        if not contract:
            raise RuntimeError(f"No contract found for {result.symbol}")
        
        # Check if we already have a position
        if result.symbol in self.positions:
            raise RuntimeError(f"Already have position in {result.symbol}")
        
        # Check max concurrent trades limit using strategy isolation
        current_active_trades = self.get_monitoring_active_orders_count()  # Uses strategy isolation
        self.logger.info(f"🎯 [{self.strategy_name}] Max concurrent trades check: {current_active_trades}/{self.max_concurrent_trades}")
        
        if current_active_trades >= self.max_concurrent_trades:
            self.logger.warning(f"🚫 [{self.strategy_name}] Cannot place order - strategy at concurrent trade limit")
            raise RuntimeError(f"Max concurrent trades limit reached ({current_active_trades}/{self.max_concurrent_trades}) for strategy {self.strategy_name}")
            
        # Determine order parameters
        action: OrderAction = "BUY" if result.trade_signal.action == "OPEN_LONG" else "SELL"
        quantity = self.default_quantity
        
        # Calculate entry price (slightly better than current price for limit order)
        entry_price = self._calculate_entry_price(result.trade_signal.entry_price, result.trade_signal.action)
        
        # Round TP and SL prices to tick increments as well
        tick_size = self._get_tick_size()
        take_profit_price = self._round_to_tick_size(result.trade_signal.take_profit, tick_size)
        stop_loss_price = self._round_to_tick_size(result.trade_signal.stop_loss, tick_size)
        
        print(f"🚀 Placing {result.trade_signal.action} bracket order for {result.symbol}")
        
        # Use appropriate decimal places for display
        if result.symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDCAD']:
            decimals = 5  # Forex major pairs
        elif result.symbol in ['USDJPY']:
            decimals = 3  # JPY pairs
        else:
            decimals = 2  # Futures/stocks
            
        print(f"   Entry: ${entry_price:.{decimals}f}")
        print(f"   Take Profit: ${take_profit_price:.{decimals}f}")
        print(f"   Stop Loss: ${stop_loss_price:.{decimals}f}")
        
        # Create bracket order using ib_async's built-in method
        bracket = self.ib.bracketOrder(
            action=action,
            quantity=quantity,
            limitPrice=entry_price,
            takeProfitPrice=take_profit_price,
            stopLossPrice=stop_loss_price
        )
        
        # Tag each order with strategy name for identification and isolation
        strategy_tag = f"STRATEGY:{self.strategy_name}|SYMBOL:{result.symbol}"
        self.logger.info(f"🏷️ [{self.strategy_name}] Tagging orders with strategy identifier: {strategy_tag}")
        
        for i, order in enumerate(bracket):
            order.orderRef = strategy_tag  # Use IBKR's orderRef field for strategy isolation
            self.logger.debug(f"   📝 Order {i+1}: ID will be assigned by IBKR, tagged with {strategy_tag}")
        
        # Place all orders from the bracket
        trades: List[Trade] = []
        for order in bracket:
            trade = self.ib.placeOrder(contract, order)
            trades.append(trade)
        
        # Use async sleep instead of ib.sleep to avoid event loop conflicts
        await asyncio.sleep(1)
        
        if not trades or len(trades) != 3:
            raise RuntimeError(f"Failed to place bracket order - expected 3 orders, got {len(trades)}")
        
        parent_trade, tp_trade, sl_trade = trades
        
        # Subscribe to Trade events for all orders
        for trade in trades:
            trade.statusEvent += lambda t, symbol=result.symbol: self._on_status_change(t, symbol, result.trade_signal)
            trade.fillEvent += lambda t, fill, symbol=result.symbol: self._on_fill(t, fill, symbol)
            trade.filledEvent += lambda t, symbol=result.symbol: self._on_filled(t, symbol, result.trade_signal)
            trade.cancelledEvent += lambda t, symbol=result.symbol: self._on_cancelled(t, symbol)
        
        # Store all Trade objects
        if result.symbol not in self.active_orders:
            self.active_orders[result.symbol] = []
        self.active_orders[result.symbol].extend(trades)
        
        # Store last price for monitoring
        self.last_prices[result.symbol] = result.trade_signal.entry_price
        
        print(f"✅ Bracket order placed successfully!")
        print(f"   Parent Order ID: {parent_trade.order.orderId}")
        print(f"   Take Profit Order ID: {tp_trade.order.orderId}")
        print(f"   Stop Loss Order ID: {sl_trade.order.orderId}")

        return PlaceOrderResult(
            parent_order_id=parent_trade.order.orderId,
            tp_order_id=tp_trade.order.orderId,
            sl_order_id=sl_trade.order.orderId,
            trades=trades,
            entry_price=entry_price,
            take_profit=take_profit_price,
            stop_loss=stop_loss_price
        )
    
    
    def analyze_current_orders(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Analyze current orders for a symbol (now much simpler with Trade events)
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Dict with analysis results
        """
        try:
            actions_taken = []
            
            # Update last price
            self.last_prices[symbol] = current_price
            
            # Check active trades for this symbol
            if symbol in self.active_orders:
                trades_to_remove = []
                
                for trade in self.active_orders[symbol]:
                    # Trade events handle most status changes automatically
                    # We just need to check for timeout or price-based cancellations
                    
                    if not trade.isDone():  # Order still active
                        # Check for order cancellation conditions
                        cancel_reason = self._should_cancel_trade(trade, current_price)
                        if cancel_reason:
                            print(f"🚫 Cancelling order {trade.order.orderId}: {cancel_reason}")
                            self.ib.cancelOrder(trade.order)
                            actions_taken.append(f"Cancelled order: {cancel_reason}")
                    else:
                        # Trade is done, remove from tracking
                        trades_to_remove.append(trade)
                
                # Remove completed trades
                for trade in trades_to_remove:
                    self.active_orders[symbol].remove(trade)
                
                # Clean up empty trade lists
                if not self.active_orders[symbol]:
                    del self.active_orders[symbol]
            
            # Check positions
            if symbol in self.positions:
                position = self.positions[symbol]
                position.update_pnl(current_price)
                
                # Check if TP/SL hit (failsafe - OCO orders should handle this)
                if self._check_position_exit_conditions(position, current_price):
                    print(f"⚠️ Failsafe: Manually closing position for {symbol}")
                    # TODO: Implement position closing logic
            
            return {
                "success": True,
                "actions_taken": actions_taken,
                "active_orders": len(self.active_orders.get(symbol, [])),
                "has_position": symbol in self.positions
            }
            
        except Exception as e:
            print(f"❌ Error analyzing orders for {symbol}: {e}")
            return {"success": False, "error": str(e)}
    
    
    
    def get_position_state(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position state for a symbol"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        return {
            "symbol": symbol,
            "direction": position.direction,
            "size": position.size,
            "entry_price": position.entry_price,
            "take_profit": position.take_profit,
            "stop_loss": position.stop_loss,
            "unrealized_pnl": position.unrealized_pnl,
            "entry_time": position.entry_time
        }
    
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all current positions"""
        return {symbol: self.get_position_state(symbol) for symbol in self.positions}
    
   
    
    def _check_position_exit_conditions(self, position: Position, current_price: float) -> bool:
        """Check if position should be closed (failsafe)"""
        if position.direction == "LONG":
            return current_price <= position.stop_loss or current_price >= position.take_profit
        else:  # SHORT
            return current_price >= position.stop_loss or current_price <= position.take_profit
    
    
    
    def _calculate_entry_price(self, current_price: float, action: str) -> float:
        """Calculate entry price for limit order (slightly better than market)"""
        # Get appropriate tick size based on symbol/asset type
        tick_size = self._get_tick_size()
        
        if action == "OPEN_LONG":
            entry_price = current_price - tick_size  # Buy slightly below market
        else:  # OPEN_SHORT
            entry_price = current_price + tick_size  # Sell slightly above market
        
        # Round to nearest tick increment
        return self._round_to_tick_size(entry_price, tick_size)
    
    def _get_tick_size(self) -> float:
        """Get appropriate tick size for the symbol"""
        # This should be configurable based on symbol, but for now:
        # Use the symbol that was just processed for tick size
        symbol = self._current_symbol
        
        if symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDCAD']:
            return 0.00005  # 0.5 pip for major forex pairs (IBKR minimum tick)
        elif symbol in ['USDJPY']:
            return 0.001    # 0.1 pip for JPY pairs (3 decimals)
        elif symbol in ['ES', 'NQ', 'YM']:
            return 0.25     # ES futures tick size
        else:
            return 0.01     # Default for stocks
    
    def _round_to_tick_size(self, price: float, tick_size: float) -> float:
        """Round price to the nearest tick increment"""
        return round(price / tick_size) * tick_size
    
    
    
    def _get_contract_type(self, symbol: str) -> ContractType:
        """Determine contract type for symbol"""
        # Simple mapping - should be enhanced based on your symbol configuration
        if symbol in ['ES', 'NQ', 'YM']:
            return "Future"
        elif symbol in ['EURUSD', 'GBPUSD', 'USDJPY']:
            return "Forex"
        else:
            return "Stock"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all orders and positions"""
        return {
            "active_orders": {symbol: len(orders) for symbol, orders in self.active_orders.items()},
            "positions": {symbol: pos.direction for symbol, pos in self.positions.items()},
            "total_unrealized_pnl": sum(pos.unrealized_pnl for pos in self.positions.values())
        }
    
    def _get_active_trades_count(self) -> int:
        """
        Get count of active trades for concurrent trade limit checking.
        For bracket orders, only count parent orders (not TP/SL children).
        
        Returns:
            int: Number of currently active parent trades across all symbols
        """
        try:
            active_count = 0
            
            # Count parent orders across all symbols
            for symbol, trades in self.active_orders.items():
                for trade in trades:
                    # Only count non-completed parent orders
                    if not trade.isDone() and trade.order.parentId == 0:
                        active_count += 1
            
            # Also count open positions
            for symbol, position in self.positions.items():
                if hasattr(position, 'size') and position.size != 0:
                    active_count += 1
            
            return active_count
            
        except Exception as e:
            print(f"❌ Error counting active trades in OrderManager: {e}")
            # Return conservative count to prevent over-trading
            return self.max_concurrent_trades
    
    def _on_status_change(self, trade: Trade, symbol: str, trade_signal):
        """Handle trade status changes"""
        print(f"📊 Order status change for {symbol}: {trade.orderStatus.status}")
    
    def _on_fill(self, trade: Trade, fill, symbol: str):
        """Handle partial fills"""
        print(f"📈 Partial fill for {symbol}: {fill.execution.shares} shares at ${fill.execution.price}")
    
    def _on_filled(self, trade: Trade, symbol: str, trade_signal):
        """Handle complete fills"""
        print(f"✅ Order filled for {symbol}: {trade.orderStatus.filled} shares")
        # TODO: Create position object and update positions dict
    
    def _on_cancelled(self, trade: Trade, symbol: str):
        """Handle order cancellations"""
        self.logger.info(f"🚫 Order cancelled for {symbol}: Order ID {trade.order.orderId}")
    
    def _should_cancel_trade(self, trade: Trade, current_price: float) -> Optional[str]:
        """Check if trade should be cancelled based on conditions"""
        # TODO: Implement cancellation logic based on order rules
        return None
    
    async def _send_fill_notification(self, trade: Trade, filled_qty: int, avg_price: float) -> None:
        """Send Telegram notification for order fills"""
        if not self.notification_manager:
            return
            
        try:
            # Determine order type based on parent relationship and order type
            parent_order_id = trade.order.parentId if hasattr(trade.order, 'parentId') and trade.order.parentId != 0 else None
            
            if parent_order_id is None:
                # This is a parent/entry order - don't send notification for these
                return
            else:
                # This is a child order (TP or SL) - send notification
                if trade.order.orderType == "STP":  # Stop order = Stop Loss
                    self.logger.info(f"🔴 [{self.strategy_name}] Stop Loss hit for {self.symbol}")
                    await self.notification_manager.notify_stop_loss_hit(
                        order_id=trade.order.orderId,
                        price=avg_price,
                        quantity=int(filled_qty),
                        pnl=0.0  # We don't have P&L data here yet
                    )
                elif trade.order.orderType == "LMT":  # Limit order = Take Profit
                    self.logger.info(f"🟢 [{self.strategy_name}] Take Profit hit for {self.symbol}")
                    await self.notification_manager.notify_take_profit_hit(
                        order_id=trade.order.orderId,
                        price=avg_price,
                        quantity=int(filled_qty),
                        pnl=0.0  # We don't have P&L data here yet
                    )
                    
        except Exception as e:
            self.logger.error(f"❌ [{self.strategy_name}] Error sending fill notification: {e}")
    
    def set_cancel_strategy(self, cancel_strategy_function: CancelStrategyFunction) -> None:
        """
        Set the cancel strategy function for order monitoring
        
        Args:
            cancel_strategy_function: Function with signature (Ticker, Trade, datetime) -> bool
        """
        self.cancel_strategy_function = cancel_strategy_function
    
    async def handle_ticker_update(self, symbol: str, ticker: Ticker) -> None:
        """
        Handle ticker updates for order monitoring with race condition protection
        
        Args:
            symbol: Trading symbol receiving ticker updates
            ticker: Real-time market data from IBKR
        """
        # Early return if no orders to monitor or no cancel strategy loaded
        if not self.monitoring_active_orders or self.cancel_strategy_function is None:
            return
            
        try:
            # Initialize lock if not already done
            if self._order_lock is None:
                self._order_lock = asyncio.Lock()
                
            # Use lock to prevent race conditions with order status changes
            async with self._order_lock:
                orders_to_cancel: List[int] = []
                
                # Create a copy to avoid modification during iteration
                current_orders = dict(self.monitoring_active_orders)
                
                for order_id, trade in current_orders.items():
                    order_time = self.monitoring_orders.get(order_id)
                    if order_time is None:
                        self.logger.warning(f"⚠️ [{self.strategy_name}] No order time found for order {order_id}")
                        continue
                    
                    # Call the cancel strategy function with proper typing
                    try:
                        should_cancel: bool = self.cancel_strategy_function(ticker, trade, order_time)
                        
                        if should_cancel:
                            orders_to_cancel.append(order_id)
                            self.logger.info(f"🚨 [{self.strategy_name}] Cancel strategy triggered for {symbol} (Order ID: {order_id})")
                            
                    except Exception as cancel_error:
                        self.logger.error(f"❌ [{self.strategy_name}] Error in cancel strategy for order {order_id}: {cancel_error}")
                        continue
                
                # Cancel the orders (still within lock)
                for order_id in orders_to_cancel:
                    await self.cancel_order(order_id)
                    
                # Stop monitoring if no more active orders for this strategy
                if not self.monitoring_active_orders:
                    self.logger.info(f"🛑 [{self.strategy_name}] No more orders to monitor - stopping ticker updates")
                    await self.stop_order_monitoring()
                    
        except Exception as e:
            self.logger.error(f"❌ [{self.strategy_name}] Error in ticker update for {symbol}: {e}")
    
    async def cancel_order(self, order_id: int) -> None:
        """
        Cancel an order through IBKR (should be called within order lock)
        
        Args:
            order_id: IBKR order ID to cancel
        """
        try:
            # Get the trade object
            trade = self.monitoring_active_orders.get(order_id)
            if trade is None:
                self.logger.warning(f"⚠️ [{self.strategy_name}] Order {order_id} not found in active orders")
                return
            
            # Cancel through IBKR
            self.ib.cancelOrder(trade.order)
            
            # Remove from monitoring (caller should have lock)
            self.monitoring_active_orders.pop(order_id, None)
            self.monitoring_orders.pop(order_id, None)
            
            self.logger.info(f"✅ [{self.strategy_name}] Successfully cancelled order {order_id}")
                
        except Exception as e:
            self.logger.error(f"❌ [{self.strategy_name}] Error cancelling order {order_id}: {e}")
    
    async def handle_order_status_change(self, trade: Trade):
        """Handle order status changes from IBKR with proper async handling and race condition protection"""
        try:
            order_id = trade.order.orderId
            status = trade.orderStatus.status
            
            self.logger.info(f"📊 [{self.strategy_name}] Order {order_id} status changed to: {status}")
            
            # Remove cancelled or filled orders from monitoring (simple approach)
            if status in ['Cancelled', 'Filled']:
                # Initialize lock if not already done
                if self._order_lock is None:
                    self._order_lock = asyncio.Lock()
                    
                # Use lock to prevent race conditions with concurrent ticker updates
                async with self._order_lock:
                    if order_id in self.monitoring_active_orders:
                        self.logger.info(f"🗑️ [{self.strategy_name}] Removing order {order_id} from monitoring (status: {status})")
                        
                        self.monitoring_active_orders.pop(order_id, None)
                        self.monitoring_orders.pop(order_id, None)
                        
                        # Log current active trades after removal
                        remaining_count = len(self.monitoring_active_orders)
                        self.logger.info(f"📈 [{self.strategy_name}] Active orders remaining for this strategy: {remaining_count}")
                        
                        # Check if we should stop monitoring entirely for this strategy
                        if not self.monitoring_active_orders:
                            self.logger.info(f"🛑 [{self.strategy_name}] No more active orders for this strategy - stopping monitoring")
                            await self.stop_order_monitoring()
                            
            # Log status for tracking
            if status == 'Filled':
                filled_qty = trade.orderStatus.filled
                avg_price = trade.orderStatus.avgFillPrice
                self.logger.info(f"✅ [{self.strategy_name}] Order filled for {self.symbol}: {filled_qty} @ {avg_price}")
                
                # Send notifications for take profit and stop loss fills
                await self._send_fill_notification(trade, filled_qty, avg_price)
                
                if self.api_manager:
                    await self.api_manager.post_executed_trade(trade)
            elif status == 'Cancelled':
                self.logger.info(f"🚫 [{self.strategy_name}] Order {order_id} cancelled")
                if self.api_manager:
                    await self.api_manager.post_order_cancel(order_id)
        except Exception as e:
            error_msg = f"❌ [{self.strategy_name}] Error in order status change handler for {self.symbol}: {e}"
            self.logger.error(error_msg)
            # Don't re-raise - we don't want to break the event system
    
    async def start_order_monitoring(self, trades: List[Trade]):
        """Start monitoring orders with cancellation conditions for this strategy"""
        if not trades:
            return False
        
        # Store the Trade objects with their order times
        order_time = datetime.now()
        for trade in trades:
            order_id = trade.order.orderId
            self.monitoring_active_orders[order_id] = trade
            self.monitoring_orders[order_id] = order_time
            self.logger.info(f"✅ [{self.strategy_name}] Started monitoring order {order_id} (Action: {trade.order.action})")
        
        # Set up order status change handlers for each trade (always needed for executed trade logging)
        for trade in trades:
            trade.statusEvent += self.handle_order_status_change
        
        # Start ticker subscription for real-time monitoring (only if cancel strategy exists)
        if self.cancel_strategy_function and self.ibkr_manager:
            success = self.ibkr_manager.start_ticker_subscription(self.symbol)
            if success:
                self.logger.info(f"✅ [{self.strategy_name}] Started ticker monitoring for {self.symbol}")
                return True
            else:
                # Cleanup if ticker subscription fails
                for trade in trades:
                    order_id = trade.order.orderId
                    self.monitoring_active_orders.pop(order_id, None)
                    self.monitoring_orders.pop(order_id, None)
                return False
        else:
            self.logger.info(f"✅ [{self.strategy_name}] Started order status monitoring for {self.symbol} (no cancel strategy)")
            return True
    
    async def stop_order_monitoring(self):
        """Stop monitoring orders and clean up"""
        print(f"🛑 Stopping order monitoring for {self.symbol}")
        
        # Debug: Check current subscriptions before stopping
        if self.ibkr_manager:
            print("🔍 Before stopping - checking IBKR subscriptions:")
            self.ibkr_manager.debug_ticker_subscriptions()
        
        if self.monitoring_active_orders:
            # Clear all monitoring state
            self.monitoring_active_orders.clear()
            self.monitoring_orders.clear()
        
        # Stop ticker subscription to save resources
        if self.ibkr_manager:
            success = self.ibkr_manager.stop_ticker_subscription(self.symbol)
            if success:
                print(f"✅ Stopped order monitoring for {self.symbol}")
            
            # Debug: Check subscriptions after stopping
            print("🔍 After stopping - checking IBKR subscriptions:")
            self.ibkr_manager.debug_ticker_subscriptions()
    
    def get_monitoring_active_orders_count(self) -> int:
        """
        Get count of active trades (distinct bracket order groups) for concurrent trade limit checking
        
        Uses IBKR as the source of truth, filtered by strategy tag and client_id.
        This ensures accurate counting even if local tracking gets out of sync.
        
        Returns:
            int: Number of distinct active trades for this strategy
        """
        self.logger.info(f"🔍 [{self.strategy_name}] Checking active trade count for strategy isolation...")
        
        try:
            # Query IBKR for authoritative order state
            ibkr_count = self._get_ibkr_strategy_trade_count()
            self.logger.info(f"✅ [{self.strategy_name}] IBKR reports {ibkr_count} active trades for this strategy")
            return ibkr_count
        except Exception as e:
            local_count = self._get_local_strategy_trade_count()
            self.logger.warning(f"⚠️ [{self.strategy_name}] Failed to query IBKR for trade count, using local tracking: {local_count} trades (Error: {e})")
            return local_count
    
    def _get_ibkr_strategy_trade_count(self) -> int:
        """
        Query IBKR for active trades belonging to this strategy (AUTHORITATIVE)
        
        Returns:
            int: Number of distinct active trades for this strategy from IBKR
        """
        if not self.ib or not self.ib.isConnected():
            raise RuntimeError("IBKR not connected")
        
        # Get all active orders/trades from IBKR
        all_trades: List[Trade] = self.ib.trades()
        strategy_tag_prefix: str = f"STRATEGY:{self.strategy_name}|SYMBOL:{self.symbol}"
        
        self.logger.debug(f"🔍 [{self.strategy_name}] Querying IBKR for strategy isolation...")
        self.logger.debug(f"📋 [{self.strategy_name}] Total trades in IBKR: {len(all_trades)}")
        self.logger.debug(f"🏷️ [{self.strategy_name}] Looking for strategy tag: {strategy_tag_prefix}")
        
        # Filter for this strategy's orders using strategy tag
        strategy_trades: List[Trade] = []
        other_strategy_count = 0
        
        for trade in all_trades:
            if hasattr(trade.order, 'orderRef') and trade.order.orderRef:
                if trade.order.orderRef.startswith(strategy_tag_prefix) and not trade.isDone():
                    strategy_trades.append(trade)
                    self.logger.debug(f"✅ [{self.strategy_name}] Found our order: {trade.order.orderId} (Parent: {trade.order.parentId}) - {trade.order.orderRef}")
                elif trade.order.orderRef.startswith("STRATEGY:") and not trade.isDone():
                    other_strategy_count += 1
                    other_strategy = trade.order.orderRef.split("|")[0].replace("STRATEGY:", "")
                    self.logger.debug(f"🔄 [{self.strategy_name}] Ignoring other strategy order: {trade.order.orderId} ({other_strategy})")
            elif not trade.isDone():
                self.logger.debug(f"📝 [{self.strategy_name}] Ignoring untagged order: {trade.order.orderId}")
        
        # Count distinct trades by grouping by parent order ID
        parent_order_ids: Set[int] = set()
        for trade in strategy_trades:
            if trade.order.parentId == 0:
                parent_order_ids.add(trade.order.orderId)
            else:
                parent_order_ids.add(trade.order.parentId)
        
        self.logger.info(f"📊 [{self.strategy_name}] Strategy isolation results:")
        self.logger.info(f"   📈 Our strategy orders: {len(strategy_trades)}")
        self.logger.info(f"   🔗 Distinct trade groups: {len(parent_order_ids)}")
        self.logger.info(f"   🚫 Other strategy orders: {other_strategy_count}")
        self.logger.info(f"   🎯 Strategy tag: {strategy_tag_prefix}")
        
        return len(parent_order_ids)
    
    def _get_local_strategy_trade_count(self) -> int:
        """
        Fallback: Count trades using local tracking (less reliable but always available)
        
        Returns:
            int: Number of distinct active trades from local tracking
        """
        # Track unique parent order IDs to count distinct trades
        parent_order_ids: Set[int] = set()
        
        for order_id, trade in self.monitoring_active_orders.items():
            # For parent orders, use their own order ID
            if trade.order.parentId == 0:
                parent_order_ids.add(order_id)
            else:
                # For child orders (TP/SL), use their parent ID to group them
                parent_order_ids.add(trade.order.parentId)
        
        return len(parent_order_ids)
    
    async def sync_with_ibkr(self) -> None:
        """
        Sync local order tracking with IBKR's authoritative state
        
        This method ensures we stay in sync even if external changes occur:
        - Orders cancelled in TWS
        - Connection issues causing missed updates
        - Manual intervention
        """
        try:
            if not self.ib or not self.ib.isConnected():
                self.logger.warning(f"⚠️ [{self.strategy_name}] Cannot sync with IBKR - not connected")
                return
            
            # Get authoritative state from IBKR
            all_trades = self.ib.trades()
            strategy_tag_prefix = f"STRATEGY:{self.strategy_name}|SYMBOL:{self.symbol}"
            
            # Find our strategy's active orders in IBKR
            ibkr_active_orders = {}
            for trade in all_trades:
                if (hasattr(trade.order, 'orderRef') and 
                    trade.order.orderRef and 
                    trade.order.orderRef.startswith(strategy_tag_prefix) and
                    not trade.isDone()):
                    ibkr_active_orders[trade.order.orderId] = trade
            
            # Find orders in local tracking that are no longer active in IBKR
            local_order_ids = set(self.monitoring_active_orders.keys())
            ibkr_order_ids = set(ibkr_active_orders.keys())
            
            # Remove orders that are done/cancelled in IBKR but still in local tracking
            stale_orders = local_order_ids - ibkr_order_ids
            for order_id in stale_orders:
                self.logger.info(f"🔄 [{self.strategy_name}] Syncing: removing stale order {order_id} from local tracking")
                self.monitoring_active_orders.pop(order_id, None)
                self.monitoring_orders.pop(order_id, None)
            
            # Add orders that are active in IBKR but missing from local tracking
            missing_orders = ibkr_order_ids - local_order_ids
            for order_id in missing_orders:
                trade = ibkr_active_orders[order_id]
                self.logger.info(f"🔄 [{self.strategy_name}] Syncing: adding missing order {order_id} to local tracking")
                self.monitoring_active_orders[order_id] = trade
                self.monitoring_orders[order_id] = datetime.now()
                
                # Set up status event handler for the newly discovered order
                trade.statusEvent += self.handle_order_status_change
            
            if stale_orders or missing_orders:
                sync_count = len(self.monitoring_active_orders)
                self.logger.info(f"✅ [{self.strategy_name}] Sync complete - now tracking {sync_count} orders")
            
        except Exception as e:
            self.logger.error(f"❌ [{self.strategy_name}] Error syncing with IBKR: {e}")
    
    def get_strategy_orders_debug_info(self) -> StrategyOrdersDebugInfo:
        """
        Get detailed debug information about strategy order isolation   
        
        Returns:
            StrategyOrdersDebugInfo with typed debug info about local vs IBKR state
        """
        strategy_tag_prefix: str = f"STRATEGY:{self.strategy_name}|SYMBOL:{self.symbol}"
        
        try:
            local_count: int = self._get_local_strategy_trade_count()
            ibkr_count: Union[int, str] = self._get_ibkr_strategy_trade_count() if self.ib and self.ib.isConnected() else "N/A"
            order_ids: List[int] = list(self.monitoring_active_orders.keys())
            in_sync: Union[bool, str] = local_count == ibkr_count if ibkr_count != "N/A" else "Unknown"
            
            return StrategyOrdersDebugInfo(
                strategy_name=self.strategy_name,
                symbol=self.symbol,
                local_trade_count=local_count,
                ibkr_trade_count=ibkr_count,
                local_order_ids=order_ids,
                in_sync=in_sync,
                strategy_tag_prefix=strategy_tag_prefix,
                error=None
            )
        except Exception as e:
            return StrategyOrdersDebugInfo(
                strategy_name=self.strategy_name,
                symbol=self.symbol,
                local_trade_count=0,
                ibkr_trade_count="ERROR",
                local_order_ids=[],
                in_sync="ERROR", 
                strategy_tag_prefix=strategy_tag_prefix,
                error=str(e)
            ) 