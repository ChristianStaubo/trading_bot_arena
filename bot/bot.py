
import sys
sys.path.append('..')
from managers.order_manager.main import PlaceOrderResult
from typing import Optional
from datetime import datetime
import asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import os
from ib_async import BarData
from managers.trade_decision_manager import CandleResult
from managers.ibkr_helper_manager import IbkrHelperManager
from managers.logging_manager import LoggingManager
from managers.trade_decision_manager import TradeDecisionManager
from managers.order_manager import OrderManager
from managers.api_manager import ApiManager
from managers.data_strategy_manager import DataAndStrategyManager
from managers.notification_manager import NotificationManager
from lib.utils.data_conversion import convert_bar_to_formatted_bar, timeframe_to_bar_size
from lib.config.settings_models import TimeframeEnum

load_dotenv()

class Bot:
    
    def __init__(self,
        name: str,
        symbol: str,
        exchange: str,
        asset_type: str,
        strategy_name: str,
        timeframe: TimeframeEnum,
        strategy_path: str,
        cancel_strategy_path: Optional[str] = None,
        max_concurrent_trades: int = 1,
        default_quantity: int = 2,
        client_id: int = 1) -> None:

        self.name = name
        self.symbol = symbol
        self.exchange = exchange
        self.asset_type = asset_type
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.strategy_path = strategy_path
        self.cancel_strategy_path = cancel_strategy_path
        self.client_id = client_id
        self.max_concurrent_trades = max_concurrent_trades
        self.default_quantity = default_quantity


        # Initialize Logging Manager (handles file + logtail logging)
        self.logging_manager = LoggingManager(
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            version="1.0.0"
        )
        self.logger = self.logging_manager.get_combined_logger()
        self.logger.info("✅ Bot configuration loaded successfully")
        
        # Initialize IBKR Helper Manager with client_id
        self.ibkr_manager = IbkrHelperManager(client_id=self.client_id)
        
        # Load strategy function
        try:
            self.strategy_function = TradeDecisionManager.load_strategy_from_file(self, strategy_path=self.strategy_path)
            self.logger.info(f"✅ Loaded strategy from {self.strategy_path}")
        except Exception as e:
            self.logger.error(f"❌ Failed to load strategy: {e}")
            raise
        
        # Single trade decision manager for this bot's symbol
        self.trade_decision_manager: Optional[TradeDecisionManager] = None

        # API manager for backend communication
        api_base_url = self._get_api_base_url()
        api_key = os.getenv("API_SECRET_KEY")
        self.api_manager = ApiManager(
            api_base_url=api_base_url,
            logger=self.logger,
            bot_name=self.name,
            symbol=self.symbol,
            strategy_name=self.strategy_name,
            api_key=api_key
        )
        self.logger.info(f"✅ API Manager configured for: {api_base_url}")
        if api_key:
            self.logger.info("🔑 API authentication enabled")
        else:
            self.logger.warning("⚠️  No API key provided - requests may fail if API requires authentication")
        
        # Notification manager for critical event alerts
        self.notification_manager = NotificationManager(
            logger=self.logger,
            bot_name=self.name,
            symbol=self.symbol,
            strategy_name=self.strategy_name
        )
        
        # Order manager for execution and monitoring
        self.order_manager = OrderManager(
            ib=self.ibkr_manager.ib,
            get_contract=self.ibkr_manager.get_contract,
            max_concurrent_trades=self.max_concurrent_trades,
            default_quantity=self.default_quantity,
            logger=self.logger,
            ibkr_manager=self.ibkr_manager,
            api_manager=self.api_manager,
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            notification_manager=self.notification_manager
        )
        
        
        
        # Data and strategy manager for initialization tasks
        self.data_strategy_manager = DataAndStrategyManager(
            ibkr_manager=self.ibkr_manager,
            logging_manager=self.logging_manager,
            logger=self.logger,
            symbol=self.symbol,
            asset_type=self.asset_type,
            timeframe=self.timeframe
        )

        
        # Set up IBKR event callbacks (after all managers are created)
        self.ibkr_manager.on_new_bar = self.onNewCandle
        self.ibkr_manager.on_ticker_update = self.order_manager.handle_ticker_update
        self.ibkr_manager.on_connected = self.onConnected
        self.ibkr_manager.on_disconnected = self.onDisconnected
        self.ibkr_manager.on_error = self.onError
        
        # Load cancel strategy function (optional) and set it in OrderManager
        if self.cancel_strategy_path:
            try:
                cancel_strategy_function = self.data_strategy_manager.load_cancel_strategy(self.cancel_strategy_path)
                self.order_manager.set_cancel_strategy(cancel_strategy_function)
                self.logger.info(f"✅ Loaded cancel strategy from {self.cancel_strategy_path}")
            except Exception as e:
                self.logger.error(f"❌ Failed to load cancel strategy: {e}")
                raise
        
        logtail_status = self.logging_manager.get_logtail_status()
        notification_status = self.notification_manager.get_status()
        self.logger.info(f"✅ Bot initialized for {self.symbol} ({strategy_name}) - Logtail: {logtail_status}, Notifications: {notification_status}")
       
    
    async def onNewCandle(self, symbol: str, bar: BarData):
        """
        Called when a new candle is received from IBKR
        
        Args:
            symbol: Symbol that the bar data is for
            bar: Raw bar data from IBKR
        """
        # Ignore bars for other symbols  
        if symbol != self.symbol:
            return
                
        try:
            bar_data = convert_bar_to_formatted_bar(bar)
            
            self.logging_manager.log_new_candle(symbol, bar)
            
            if self.trade_decision_manager:
                self.logger.info(f"🔄 Processing candle through TradeDecisionManager for {symbol}")
                
                # 1. Get pure trading decision
                trading_decision: CandleResult = self.trade_decision_manager.process_new_candle(bar_data)

                self.logger.info(f"📊 Trade decision result: {trading_decision}")                
                
                # 2. Execute trades based on decision
                if trading_decision.trade_signal:
                    self.logger.info(f"🚨 [{self.strategy_name}] Trade signal for {symbol}: {trading_decision.trade_signal.action}")
                    
                    # Check if we can trade based on business rules
                    if self.can_trade:
                        order_result = await self.place_order(trading_decision)
                        self.logger.info(f"✅ [{self.strategy_name}] Order placed for {symbol}: ID {order_result.parent_order_id}")
                        
                        await self.order_manager.start_order_monitoring(order_result.trades)
                        
                        await self.api_manager.post_order(order_result)
                    else:
                        self.logger.info(f"⏸️ [{self.strategy_name}] Trade signal received but trading not allowed - skipping order placement")

                    # Always log the trade signal regardless of whether we place order
                    await self.api_manager.post_trade_signal(
                        trading_decision.trade_signal, 
                        self.timeframe.value,  # Convert enum to string value
                        self.order_manager.get_monitoring_active_orders_count(), 
                        self.max_concurrent_trades,
                    )
                
            else:
                self.logger.warning(f"⚠️ TradeDecisionManager not initialized for {symbol}")
                
        except Exception as e:
            self.logger.error(f"❌ Error in onNewCandle: {e}")
    
    
    def onConnected(self) -> None:
        """Called when IBKR connection is established"""
        self.logging_manager.log_connection_event("connected")
    
    def onDisconnected(self) -> None:
        """Called when IBKR connection is lost"""
        self.logging_manager.log_connection_event("disconnected")
    
    async def onError(self, error_code: int, error_string: str, req_id: int) -> None:
        """
        Called when IBKR error occurs
        
        Args:
            error_code: IBKR error code (e.g., 1100, 10182)
            error_string: Human-readable error message
            req_id: Request ID (-1 for general errors)
        """
        self.logger.error(f"🚨 IBKR Error {error_code}: {error_string} (reqId: {req_id})")
        
        # Handle specific connection loss errors
        if error_code == 1100:
            # Connectivity between IBKR and TWS has been lost
            success = await self.notification_manager.notify_connection_lost(
                error_details=f"Error {error_code}: {error_string}"
            )
            if success:
                self.logger.warning(f"📢 Sent connection lost notification for error {error_code}")
            else:
                self.logger.error(f"❌ Failed to send connection lost notification for error {error_code}")
            
        elif error_code == 1102:
            # Connection restored
            success = await self.notification_manager.notify_connection_restored()
            if success:
                self.logger.info(f"📢 Sent connection restored notification for error {error_code}")
            else:
                self.logger.error(f"❌ Failed to send connection restored notification for error {error_code}")
            
        elif error_code == 10182:
            # Failed to request live updates (disconnected)
            # This is often a secondary error after 1100, so we'll log it but not duplicate notifications
            self.logger.warning(f"🔄 Live data subscription lost due to disconnection (Error {error_code})")
            # Could add a different notification type here if needed
    
    @property
    def can_trade(self) -> bool:
        """
        Determine if the bot can currently place trades based on various business rules
        
        This property centralizes all trading constraints and can be extended with:
        - Time-based restrictions (market hours, specific times)
        - Risk management rules (daily limits, drawdown limits)
        - External factors (news events, volatility conditions)
        - Strategy-specific conditions
        
        Returns:
            bool: True if trading is currently allowed, False otherwise
        """
        # Check max concurrent trades limit for this strategy
        current_active_trades = self.order_manager.get_monitoring_active_orders_count()
        
        if current_active_trades >= self.max_concurrent_trades:
            self.logger.info(f"⚠️ [{self.strategy_name}] Cannot trade - max concurrent trades reached ({current_active_trades}/{self.max_concurrent_trades})")
            self.logger.info(f"💡 [{self.strategy_name}] Note: Other strategies may still be able to place orders independently")
            return False
        
        # Future extension points:
        # - Time-based restrictions
        # - Risk management checks  
        # - Market condition filters
        # - Strategy-specific rules
        
        self.logger.debug(f"📊 [{self.strategy_name}] Trading allowed - active trades: {current_active_trades}/{self.max_concurrent_trades}")
        return True

    async def place_order(self, trading_decision: CandleResult) -> PlaceOrderResult:
        """
        Place an order based on the trading decision
        
        Args:
            trading_decision: Trade decision containing signal and risk parameters
            
        Returns:
            PlaceOrderResult: Order placement details
            
        Raises:
            RuntimeError: If order placement fails for any reason
        """
        self.logger.info(f"📈 [{self.strategy_name}] PLACING order - proceeding with order placement")
        order_result = await self.order_manager.place_order(trading_decision)
        return order_result
    
    async def initialize_strategy(self) -> None:
        """Initialize the trading strategy for this bot's symbol"""
        self.logger.info(f"🔄 Initializing strategy for {self.symbol}...")
        
        try:
            # Create and qualify contract using IBKR manager
            contract = await self.ibkr_manager.create_and_qualify_contract(
                self.symbol, self.asset_type, self.exchange
            )
            
            if not contract:
                self.logger.error(f"❌ Could not create/qualify contract for {self.symbol}")
                raise RuntimeError(f"Failed to create contract for {self.symbol}")
            
            # Wait a moment for IBKR to be ready for data requests
            self.logger.info("⏱️ Waiting for IBKR to be ready for data requests...")
            await asyncio.sleep(3)
            
            # Use DataAndStrategyManager to initialize strategy data
            self.trade_decision_manager = await self.data_strategy_manager.initialize_strategy_data(
                symbol=self.symbol,
                contract=contract,
                timeframe=self.timeframe,
                strategy_function=self.strategy_function
            )
            
            if self.trade_decision_manager is None:
                raise RuntimeError(f"Failed to initialize strategy data for {self.symbol}")
            
            self.logger.info(f"✅ Strategy initialized for {self.symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing strategy for {self.symbol}: {e}")
            raise
    
    
    
    async def start_real_time_data(self) -> None:
        """Start real-time data subscriptions"""
        self.logger.info("📡 Starting real-time data subscriptions...")
        
        for symbol in self.ibkr_manager.get_active_symbols():
            await self.data_strategy_manager.setup_real_time_data(symbol, self.timeframe)
        
        self.logger.info("✅ Real-time data subscriptions complete")
    
    async def run_async(self) -> None:
        """
        Main async run method - contains the complete bot lifecycle
        
        This method handles:
        - IBKR connection and contract qualification
        - Strategy initialization with historical data
        - Real-time data subscription setup
        - Main event loop with heartbeat monitoring
        """
        try:
            self.logger.info(f"🚀 Starting {self.symbol} bot...")
            
            # Connect to IBKR first
            self.logger.info("🔌 Connecting to IBKR...")
            if await self.ibkr_manager.connect():
                self.logging_manager.log_connection_event("connected")
                self.logger.info(f"✅ {self.symbol} bot connected to IBKR successfully")
                
                # Create and qualify contract
                contract = await self.ibkr_manager.create_and_qualify_contract(
                    symbol=self.symbol,
                    asset_type=self.asset_type,
                    exchange=self.exchange
                )
                
                if contract:
                    self.logger.info(f"✅ Contract qualified for {self.symbol}")
                    
                    # Initialize strategy with historical data
                    await self.initialize_strategy()
                    
                    # Start real-time data using our data strategy manager
                    await self.start_real_time_data()
                    
                    self.logger.info("🚀 Bot is now running and listening for data...")
                    self.logger.info(f"📊 Monitoring {self.symbol} with {self.strategy_name}")
                    self.logger.info(f"📋 Timeframe: {timeframe_to_bar_size(self.timeframe)}")
                    
                    # Notify that bot has started
                    await self.notification_manager.notify_bot_started()
                    
                    # Keep the bot running with heartbeat
                    while True:
                        await asyncio.sleep(60)  # Heartbeat every minute
                        self.logger.info(f"💓 Bot heartbeat - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    self.logger.error(f"❌ Failed to qualify contract for {self.symbol}")
                    raise RuntimeError(f"Contract qualification failed for {self.symbol}")
            else:
                self.logging_manager.log_connection_event("error", "Failed to connect to IBKR")
                self.logger.error(f"❌ Failed to connect {self.symbol} bot to IBKR")
                raise ConnectionError("Could not connect to IBKR")
                
        except KeyboardInterrupt:
            self.logger.info(f"🛑 {self.symbol} bot shutdown requested")
        except Exception as e:
            self.logger.error(f"❌ {self.symbol} bot error: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("🧹 Cleaning up bot resources...")
        
        try:
            # Log order/position summary before cleanup
            summary = self.order_manager.get_summary()
            if summary["active_orders"] or summary["positions"]:
                self.logger.info(f"📊 Final summary: {summary}")
            
            # Disconnect from IBKR using manager
            if self.ibkr_manager.is_connected():
                self.ibkr_manager.disconnect()
                self.logging_manager.log_connection_event("disconnected", "Bot cleanup")
                
                # Give IBKR time to disconnect properly
                await asyncio.sleep(1)
            
            # Cleanup logging manager
            self.logging_manager.cleanup()
            
            print(f"✅ Bot cleanup completed for {self.symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error during cleanup: {e}")
            print(f"❌ Cleanup error: {e}")
                        
    def __del__(self) -> None:
        """Destructor to ensure cleanup on garbage collection"""
        try:
            if hasattr(self, 'ibkr_manager') and self.ibkr_manager.is_connected():
                self.ibkr_manager.disconnect()
                print(f"🧹 Emergency cleanup: Disconnected {self.symbol} bot")
        except:
            pass  # Ignore errors in destructor

    def _get_api_base_url(self) -> str:
        """
        Get API base URL based on environment configuration.
        
        Returns:
            str: API base URL for the current environment
        """
        # Check for explicit API_BASE_URL first
        api_base_url = os.getenv("API_BASE_URL")
        if api_base_url:
            return api_base_url
        
        # Fallback to environment-based logic
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if environment == "production":
            return "https://tradingbotapi-production-d8c1.up.railway.app/api/v1"
        else:
            # Development or any other environment defaults to localhost
            return "http://localhost:8000/api/v1"

    def run(self) -> None:
        """
        Main run method - entry point for MultiProcessManager
        
        This is a simple sync wrapper that delegates to run_async() for the actual implementation.
        """
        asyncio.run(self.run_async())

if __name__ == "__main__":
    # Use MultiProcessManager for all bot orchestration
    from managers.multi_process_manager import MultiProcessManager
    
    # Create and run the bot system
    manager = MultiProcessManager()
    manager.run_system()