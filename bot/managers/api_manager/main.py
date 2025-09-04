"""
API Manager for Bot Communication

Handles all API communication between the bot and the backend service.
Centralizes HTTP requests, error handling, and response processing.
"""

import aiohttp
import json
from typing import Optional, TYPE_CHECKING
from .models.commision_and_pnl_data_model import CommissionAndPnlData
from managers.trade_decision_manager.types import TradeSignal
from managers.order_manager.main import PlaceOrderResult
from ib_async import Trade

if TYPE_CHECKING:
    from managers.logging_manager import CombinedLogger




class ApiManager:
    """
    Manages all API communication for the trading bot
    
    Responsibilities:
    - POST trade signals to backend
    - POST order details to backend  
    - POST executed trades to backend
    - POST order cancellations to backend
    - Handle HTTP errors and retries
    """
    
    def __init__(self, 
                 api_base_url: str, 
                 logger: 'CombinedLogger', 
                 bot_name: str, 
                 symbol: str, 
                 strategy_name: str,
                 api_key: Optional[str] = None):
        """
        Initialize API Manager
        
        Args:
            api_base_url: Base URL for the API (e.g., "http://localhost:8000/api/v1")
            logger: CombinedLogger instance for error reporting and debugging
            bot_name: Name of the bot instance
            symbol: Trading symbol
            strategy_name: Name of the trading strategy
            api_key: API key for authentication (optional)
        """
        self.api_base_url = api_base_url
        self.logger = logger
        self.bot_name = bot_name
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.api_key = api_key
    
    def _get_headers(self) -> dict:
        """Get HTTP headers including authentication if API key is provided"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def post_trade_signal(self, 
                               trade_signal: TradeSignal, 
                               timeframe: str,
                               current_active_trades: int, 
                               max_concurrent_trades: int,
                               ) -> None:
        """
        POST trade signal to API
        
        Args:
            trade_signal: Trading signal with entry/exit details
            timeframe: Trading timeframe (e.g., "1min", "5min")
            current_active_trades: Current number of active trades for this strategy
            max_concurrent_trades: Maximum allowed concurrent trades
            order_placed: Whether an order was actually placed for this signal
        """
        try:
            print(f"📤 [API] Posting trade signal - {trade_signal}")
            self.logger.info(f"📤 [API] Posting trade signal - {trade_signal}")
            data = {
                "bot_name": self.bot_name,
                "symbol": self.symbol,
                "strategy_name": self.strategy_name,
                "timeframe": timeframe,
                "action": trade_signal.action,
                "entry_price": float(trade_signal.entry_price),
                "stop_loss": float(trade_signal.stop_loss) if trade_signal.stop_loss else None,
                "take_profit": float(trade_signal.take_profit) if trade_signal.take_profit else None,
                "reason": getattr(trade_signal, 'reason', None),
                "max_concurrent_trades": max_concurrent_trades,
                "current_active_trades": current_active_trades,
            }
            
            self.logger.debug(f"📋 [API] Trade signal payload: {json.dumps(data, indent=2)}")
                         
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/trades/trade-signals",
                    json=data,
                    headers=self._get_headers()
                ) as response:
                    print(f"📤 [API] Trade signal posted - {response}")
                    pass  # Handled in API
                     
        except Exception:
            pass  # Handled in API
    
    async def post_order(self, order_result: PlaceOrderResult) -> None:
        """
        POST order placement event to API
        
        Records the high-level order placement attempt (success/failure) without
        IBKR-specific details. Individual IBKR orders are tracked separately via post_executed_trade.
        
        Args:
            order_result: Result from order placement attempt
        """
        try:
            self.logger.info(f"📤 [API] Posting order result - {order_result}")
            # Determine if order placement was successful
            success = order_result.trades is not None and len(order_result.trades) > 0
            
            data = {
                "bot_name": self.bot_name,
                "symbol": self.symbol,
                "success": success,
                "error": None if success else "Order placement failed",
                "stop_loss": float(order_result.stop_loss) if order_result.stop_loss else None,
                "take_profit": float(order_result.take_profit) if order_result.take_profit else None,
                "trade_count": len(order_result.trades) if order_result.trades else 0
            }
            
            self.logger.info(f"📤 [API] Posting order result - {data['symbol']} success: {data['success']}")
            self.logger.debug(f"📋 [API] Order payload: {json.dumps(data, indent=2)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/trades/orders",
                    json=data,
                    headers=self._get_headers()
                ) as response:
                    pass  # Handled in API
                     
        except Exception as e:
            pass  # Handled in API
    
    async def post_executed_trade(self, trade: Trade) -> None:
        """
        POST executed trade to API focusing on key trading metrics
        
        Captures essential trading data: order type, P&L, commission, quantity,
        parent/child relationships, and order purpose for analysis.
        
        Args:
            trade: IBKR Trade object with execution details
        """
        try:
            self.logger.info(f"📤 [API] Posting executed trade - {trade}")
            # Determine order purpose and parent relationship
            parent_order_id = trade.order.parentId if trade.order.parentId != 0 else None
            order_purpose = self._determine_order_purpose(trade, parent_order_id)
            
            
            
            # Extract commission and P&L from fills
            commission_info = self._extract_commission_and_pnl(trade)
            
            data = {
                "bot_name": self.bot_name,
                "symbol": self.symbol,
                "ibkr_order_id": trade.order.orderId,
                "ibkr_contract_id": getattr(trade.contract, 'conId', None),
                "ibkr_parent_order_id": parent_order_id,
                "action": trade.order.action,
                "order_type": trade.order.orderType,
                "order_purpose": order_purpose,
                "total_quantity": int(trade.order.totalQuantity),
                "limit_price": float(trade.order.lmtPrice) if hasattr(trade.order, 'lmtPrice') and trade.order.lmtPrice else None,
                "aux_price": float(trade.order.auxPrice) if hasattr(trade.order, 'auxPrice') and trade.order.auxPrice else None,
                "status": trade.orderStatus.status,
                "filled_quantity": int(trade.orderStatus.filled),
                "remaining_quantity": int(trade.orderStatus.remaining),
                "avg_fill_price": float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
                "last_fill_price": float(trade.orderStatus.lastFillPrice) if trade.orderStatus.lastFillPrice else None,
                "commission": commission_info.commission,
                "realized_pnl": commission_info.realized_pnl,
                "exchange": getattr(trade.contract, 'exchange', None),
                "currency": getattr(trade.contract, 'currency', None)
            }
            
            self.logger.info(f"📤 [API] Posting executed trade - {data['symbol']} {data['action']} {data['order_type']} (ID: {data['ibkr_order_id']})")
            self.logger.debug(f"📋 [API] Executed trade payload: {json.dumps(data, indent=2)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/trades/executed-trades",
                    json=data,
                    headers=self._get_headers()
                ) as response:
                    pass  # Handled in API
                     
        except Exception as e:
            pass  # Handled in API
    
    def _determine_order_purpose(self, trade: Trade, parent_order_id: Optional[int]) -> Optional[str]:
        """
        Determine the purpose of an order (ENTRY, TAKE_PROFIT, STOP_LOSS)
        
        Args:
            trade: IBKR Trade object
            parent_order_id: Parent order ID if this is a child order
            
        Returns:
            Order purpose string or None
        """
        if parent_order_id is None:  # This is a parent/entry order
            return "ENTRY"
        else:  # This is a child order (TP or SL)
            if trade.order.orderType == "STP":  # Stop order = Stop Loss
                return "STOP_LOSS"
            elif trade.order.orderType == "LMT":  # Limit order = Take Profit
                return "TAKE_PROFIT"
            return None
    
    def _extract_commission_and_pnl(self, trade: Trade) -> CommissionAndPnlData:
        """
        Extract commission and realized P&L from trade fills
        
        Args:
            trade: IBKR Trade object with potential fills
            
        Returns:
            CommissionAndPnlData: Type-safe model with commission and realized_pnl
        """
        total_commission = 0.0
        total_realized_pnl = 0.0
        has_commission_data = False
        
        try:
            if hasattr(trade, 'fills') and trade.fills:
                for fill in trade.fills:
                    if hasattr(fill, 'commissionReport') and fill.commissionReport:
                        commission_report = fill.commissionReport
                        
                        # Extract commission
                        if hasattr(commission_report, 'commission') and commission_report.commission:
                            total_commission += float(commission_report.commission)
                            has_commission_data = True
                        
                        # Extract realized P&L
                        if hasattr(commission_report, 'realizedPNL') and commission_report.realizedPNL:
                            total_realized_pnl += float(commission_report.realizedPNL)
        except (AttributeError, ValueError, TypeError):
            pass
        
        return CommissionAndPnlData(
            commission=total_commission if has_commission_data else None,
            realized_pnl=total_realized_pnl if has_commission_data else None
        )
    
    async def post_order_cancel(self, order_id: int) -> None:
        """
        POST order cancellation to API
        
        Args:
            order_id: IBKR order ID that was cancelled
        """
        try:
            self.logger.info(f"📤 [API] Posting order cancellation - {order_id}")
            data = {
                "bot_name": self.bot_name,
                "symbol": self.symbol,
                "ibkr_order_id": order_id,
                "reason": "strategy_cancel"  # Could be "manual_cancel", "timeout", etc.
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/trades/order-cancellations",
                    json=data,
                    headers=self._get_headers()
                ) as response:
                    pass  # Handled in API
                     
        except Exception as e:
            pass  # Handled in API