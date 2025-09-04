"""
Data and Strategy Manager for Trading Bot

Handles both data fetching operations and strategy loading for the trading bot.
This manager centralizes all data-related and strategy-related initialization tasks.
"""

import asyncio
import importlib.util
from logging import Logger
import os
import pandas as pd
from typing import Optional, TYPE_CHECKING, Callable
from datetime import datetime

from ib_async import Contract
from lib.types.cancel_strategy import CancelStrategyFunction, validate_cancel_strategy_function
from managers.trade_decision_manager import TradeDecisionManager
from lib.config.settings_models import TimeframeEnum
from lib.utils.data_conversion import timeframe_to_bar_size

# Import manager types for proper type hinting
if TYPE_CHECKING:
    from managers.ibkr_helper_manager import IbkrHelperManager
    from managers.logging_manager import LoggingManager


class DataAndStrategyManager:
    """
    Manages data fetching and strategy loading for the trading bot
    
    Responsibilities:
    - Fetch historical data from IBKR with retry logic
    - Setup real-time data subscriptions  
    - Load and validate cancel strategy functions
    - Initialize TradeDecisionManager with data
    - Handle data-related error recovery
    """
    
    def __init__(self, 
                 ibkr_manager: 'IbkrHelperManager',
                 logging_manager: 'LoggingManager',
                 logger: Logger,
                 symbol: str,
                 asset_type: str,
                 timeframe: TimeframeEnum):
        """
        Initialize Data and Strategy Manager
        
        Args:
            ibkr_manager: IBKR helper manager instance
            logging_manager: Logging manager instance
            logger: Logger instance for this manager
            symbol: Trading symbol
            asset_type: Asset type (forex, futures, etc.)
            timeframe: Trading timeframe
        """
        self.ibkr_manager: 'IbkrHelperManager' = ibkr_manager
        self.logging_manager: 'LoggingManager' = logging_manager
        self.logger: Logger = logger
        self.symbol: str = symbol
        self.asset_type: str = asset_type
        self.timeframe: TimeframeEnum = timeframe
    
    def load_cancel_strategy(self, strategy_path: str) -> CancelStrategyFunction:
        """
        Load and validate cancel strategy function from file
        
        Args:
            strategy_path: Path to the cancel strategy Python file
            
        Returns:
            CancelStrategyFunction: Function with signature (Ticker, Trade, datetime) -> bool
            
        Raises:
            ValueError: If the file doesn't exist or doesn't contain the required function
        """
        # Get absolute path
        if not os.path.isabs(strategy_path):
            strategy_path = os.path.abspath(strategy_path)
        
        # Load module from file
        spec = importlib.util.spec_from_file_location("cancel_strategy", strategy_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load cancel strategy from {strategy_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the should_cancel_order function
        if not hasattr(module, 'should_cancel_order'):
            raise ValueError(f"Cancel strategy file {strategy_path} must contain 'should_cancel_order' function")
        
        cancel_function = module.should_cancel_order
        
        try:
            validate_cancel_strategy_function(cancel_function)
        except ValueError as e:
            raise ValueError(f"Invalid cancel strategy function in {strategy_path}: {e}")
        
        return cancel_function
    
    async def fetch_historical_data(self, symbol: str, contract: Contract, timeframe: TimeframeEnum) -> pd.DataFrame:
        """
        Fetch historical data from IBKR for a symbol with retry logic and error handling
        
        Args:
            symbol: Trading symbol
            contract: IBKR contract
            timeframe: Timeframe (e.g., TimeframeEnum.ONE_MINUTE)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            self.logger.info(f"📊 Requesting historical data for {symbol}: {timeframe}")
            self.logger.info(f"📊 Contract: {contract}")
            self.logger.info(f"📊 Contract details: conId={getattr(contract, 'conId', 'N/A')}, exchange={contract.exchange}")
            self.logger.info(f"📊 IBKR connection status: {self.ibkr_manager.ib.isConnected()}")
            
            # Add small delay before requesting data
            await asyncio.sleep(1)
            
            try:
                # Request historical data
                self.logger.info("📊 Making reqHistoricalData call...")
                
                # Use appropriate duration and whatToShow based on asset type
                if self.asset_type.lower() == "forex":
                    duration = '2 D'  # Use longer duration like the working example
                    what_to_show = 'MIDPOINT'  # Forex uses midpoint data
                else:
                    duration = '1 D'  # Shorter duration for futures
                    what_to_show = 'TRADES'  # Futures and stocks use trades
                
                self.logger.info(f"📊 Using duration: {duration}, whatToShow: {what_to_show} for {self.asset_type}")
                
                bars = await self.ibkr_manager.ib.reqHistoricalDataAsync(
                    contract=contract,
                    endDateTime='',
                    durationStr=duration,  
                    barSizeSetting=timeframe_to_bar_size(timeframe),
                    whatToShow=what_to_show,
                    useRTH=False,  # Include extended hours (especially important for forex 24/5)
                    formatDate=1
                )
                
                self.logger.info(f"📊 reqHistoricalData completed")
                self.logger.info(f"📊 IBKR returned {len(bars) if bars else 0} bars")
                self.logger.info(f"📊 Bars type: {type(bars)}")
                
            except Exception as e:
                self.logger.error(f"❌ Exception during reqHistoricalData: {e}")
                return pd.DataFrame()
            
            if not bars:
                self.logger.warning(f"⚠️ No bars returned from IBKR for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for bar in bars:
                data.append({
                    'Open': float(bar.open),
                    'High': float(bar.high),
                    'Low': float(bar.low),
                    'Close': float(bar.close),
                    'Volume': float(bar.volume),
                    'timestamp': bar.date
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df.index = pd.to_datetime(df.index)
            
            self.logger.info(f"✅ Successfully fetched {len(df)} historical {timeframe} bars for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching historical data for {symbol}: {e}")
            self.logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return pd.DataFrame()
    
    async def setup_real_time_data(self, symbol: str, timeframe: TimeframeEnum) -> None:
        """
        Setup real-time data subscriptions for a symbol
        
        Args:
            symbol: Trading symbol
            timeframe: Trading timeframe
            
        Raises:
            RuntimeError: If real-time data setup fails
        """
        self.logger.info(f"📡 Setting up real-time data for {symbol}...")
        
        # Start real-time data using IBKR manager
        success = await self.ibkr_manager.start_real_time_data(symbol, timeframe_to_bar_size(timeframe))
        
        if success:
            self.logger.info(f"📊 Started streaming {timeframe} bars for {symbol}")
            
            instrument_logger = self.logging_manager.get_instrument_logger(symbol)
            if instrument_logger:
                instrument_logger.info(f"📡 Streaming {timeframe} bars subscription started for {symbol}")
                instrument_logger.info(f"📡 Note: New bars will stream in real-time during market hours")
        else:
            raise RuntimeError(f"Failed to start real-time data for {symbol}")
    
    async def initialize_strategy_data(self, 
                                     symbol: str, 
                                     contract: Contract, 
                                     timeframe: TimeframeEnum, 
                                     strategy_function: Callable) -> Optional[TradeDecisionManager]:
        """
        Complete strategy initialization: fetch data + create TradeDecisionManager
        
        Args:
            symbol: Trading symbol
            contract: IBKR contract
            timeframe: Trading timeframe
            strategy_function: Strategy function for signal generation
            
        Returns:
            TradeDecisionManager instance if successful, None if failed
        """
        try:
            self.logger.info(f"🔄 Initializing strategy data for {symbol}...")
            
            # Get historical data from IBKR (with retry logic)
            historical_data = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"📊 Fetching historical data for {symbol} (attempt {attempt + 1}/{max_retries})")
                    historical_data = await self.fetch_historical_data(symbol, contract, timeframe)
                    
                    if not historical_data.empty:
                        break
                    else:
                        self.logger.warning(f"⚠️ No data returned on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)  # Wait before retry
                except Exception as e:
                    self.logger.warning(f"⚠️ Data fetch attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
            
            if historical_data is None or historical_data.empty:
                self.logger.error(f"❌ No historical data for {symbol} after {max_retries} attempts")
                return None
            
            # Create TradeDecisionManager for this symbol
            trade_decision_manager = TradeDecisionManager(
                symbol=symbol,
                strategy_function=strategy_function,
                historical_window=200,
                min_data_points=50
            )
            
            # Add historical data to TradeDecisionManager
            if not trade_decision_manager.add_historical_data(historical_data):
                self.logger.error(f"❌ Failed to initialize TradeDecisionManager for {symbol}")
                return None
            
            
            self.logger.info(f"✅ Strategy data initialized for {symbol}")
            return trade_decision_manager
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing strategy data for {symbol}: {e}")
            return None