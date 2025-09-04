import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from lib.models.data_models import FormattedBar
from .types import (
    TradeAction, ConfidenceLevel, StrategyFunction, 
    TradeSignal, StrategySignalResult, CandleResult
)

import pandas as pd
import numpy as np
from typing import Callable, Optional, Dict, List, Any
from datetime import datetime
import importlib.util
class TradeDecisionManager:
    """
    Manages pure strategy execution and trade decisions for a single symbol.
    
    Handles:
    - Rolling historical data window
    - Strategy execution on new candles
    - Trade signal generation
    - Returns pure trade decisions without position awareness
    """
    
    def __init__(self, 
                 symbol: str,
                 strategy_function: StrategyFunction,
                 historical_window: int = 200,
                 min_data_points: int = 50):
        """
        Initialize TradeDecisionManager for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'ES', 'EURUSD')
            strategy_function: Function that takes DataFrame and returns DataFrame with signals
            historical_window: Number of candles to maintain in rolling window
            min_data_points: Minimum candles needed before generating signals
        """
        self.symbol = symbol
        self.strategy_function = strategy_function
        self.historical_window = historical_window
        self.min_data_points = min_data_points
        
        # Historical OHLCV data (rolling window)
        self.historical_data = pd.DataFrame()
        
        # Current strategy state
        self.current_signal = 0  # -1, 0, 1
        self.current_take_profit = 0.0
        self.current_stop_loss = 0.0
        
        # Initialize with standard OHLCV columns
        self._initialize_dataframe()
    
    def _initialize_dataframe(self):
        """Initialize the historical data DataFrame with proper columns"""
        self.historical_data = pd.DataFrame(columns=[
            'Open', 'High', 'Low', 'Close', 'Volume', 'timestamp'
        ])
        self.historical_data.set_index('timestamp', inplace=True)
    
    def add_historical_data(self, df: pd.DataFrame) -> bool:
        """
        Add bulk historical data to initialize the manager
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure we have the right columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                return False
            
            # Copy and prepare data
            hist_data = df[required_columns].copy()
            
            # Ensure we have a datetime index
            if not isinstance(hist_data.index, pd.DatetimeIndex):
                # Assume index is already timestamp, convert if needed
                hist_data.index = pd.to_datetime(hist_data.index)
            
            # Keep only the most recent data within our window
            if len(hist_data) > self.historical_window:
                hist_data = hist_data.tail(self.historical_window)
            
            self.historical_data = hist_data
            
            # Run initial strategy calculation if we have enough data
            if len(self.historical_data) >= self.min_data_points:
                self._update_strategy_signals()
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding historical data for {self.symbol}: {e}")
            return False
    
    def process_new_candle(self, candle_data: FormattedBar) -> CandleResult:
        """
        Process a new candle and generate pure trade decisions
        
        This method:
        1. Updates strategy signals
        2. Returns trade decisions without position awareness
        
        Args:
            candle_data: Dictionary with keys: time, open, high, low, close, volume
            
        Returns:
            CandleResult with signal information
            
        Raises:
            Exception: If strategy processing fails or data conversion errors occur
        """
        current_price = float(candle_data.close)
        
        # Convert candle data to DataFrame row
        new_row = pd.DataFrame({
            'Open': [float(candle_data.open)],
            'High': [float(candle_data.high)],
            'Low': [float(candle_data.low)],
            'Close': [current_price],
            'Volume': [float(candle_data.volume)]
        }, index=[pd.to_datetime(candle_data.time)])
        
        # Add to historical data
        self.historical_data = pd.concat([self.historical_data, new_row])
        
        # Maintain rolling window size
        if len(self.historical_data) > self.historical_window:
            self.historical_data = self.historical_data.tail(self.historical_window)
        
        # Update strategy signals if we have enough data
        if len(self.historical_data) >= self.min_data_points:
            signal_result = self._update_strategy_signals()
            
            # If strategy execution failed, let the error propagate
            if signal_result.error:
                raise RuntimeError(f"Strategy execution failed: {signal_result.error}")
            
            # Create trade signal if we have a valid signal
            trade_signal = None
            if signal_result.new_signal != 0:
                action = TradeAction.OPEN_LONG if signal_result.new_signal == 1 else TradeAction.OPEN_SHORT
                
                # Determine confidence based on signal strength (can be enhanced with more logic)
                confidence = ConfidenceLevel.MEDIUM  # Default, can be improved with indicator analysis
                
                trade_signal = TradeSignal(
                    action=action,
                    entry_price=current_price,
                    take_profit=signal_result.take_profit,
                    stop_loss=signal_result.stop_loss,
                    confidence=confidence,
                    indicators=signal_result.indicators
                )
            
            return CandleResult(
                symbol=self.symbol,
                trade_signal=trade_signal,
                current_price=current_price,
                signal_changed=signal_result.signal_changed
            )
        else:
            # Not enough data yet
            return CandleResult(
                symbol=self.symbol,
                trade_signal=None,
                current_price=current_price,
                signal_changed=False
            )
    
    def _update_strategy_signals(self) -> StrategySignalResult:
        """
        Apply strategy function to current data and update signals
        
        Returns:
            StrategySignalResult with typed signal information
        """
        try:
            # Apply strategy function
            strategy_result = self.strategy_function(self.historical_data.copy())
            
            # Get the latest signal (last row)
            if len(strategy_result) > 0:
                latest = strategy_result.iloc[-1]
                
                new_signal = int(latest.get('Trade_Signal', 0))
                new_take_profit = float(latest.get('Take_Profit', 0.0))
                new_stop_loss = float(latest.get('Stop_Loss', 0.0))
                
                # Check if signal changed
                signal_changed = new_signal != self.current_signal
                
                # Update current state
                old_signal = self.current_signal
                self.current_signal = new_signal
                self.current_take_profit = new_take_profit
                self.current_stop_loss = new_stop_loss
                
                return StrategySignalResult(
                    symbol=self.symbol,
                    old_signal=old_signal,
                    new_signal=new_signal,
                    signal_changed=signal_changed,
                    take_profit=new_take_profit,
                    stop_loss=new_stop_loss,
                    current_price=float(latest.get('Close', 0)),
                    indicators=self._extract_indicators(latest),
                    error=None
                )
            
            return StrategySignalResult(
                symbol=self.symbol,
                old_signal=0,
                new_signal=0,
                signal_changed=False,
                take_profit=0.0,
                stop_loss=0.0,
                current_price=0.0,
                error='No strategy result data'
            )
            
        except Exception as e:
            return StrategySignalResult(
                symbol=self.symbol,
                old_signal=0,
                new_signal=0,
                signal_changed=False,
                take_profit=0.0,
                stop_loss=0.0,
                current_price=0.0,
                error=f"Strategy execution error: {str(e)}"
            )
    
    def _extract_indicators(self, latest_row) -> Dict[str, float]:
        """Extract technical indicators from the latest strategy result"""
        indicators = {}
        
        # Common indicators to extract
        indicator_columns = ['BB_Upper', 'BB_Lower', 'SMA', 'BB_Width', 'RSI', 'ATR']
        
        for col in indicator_columns:
            if col in latest_row:
                indicators[col] = float(latest_row[col])
        
        return indicators
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the trade decision manager"""
        return {
            'symbol': self.symbol,
            'data_points': len(self.historical_data),
            'current_signal': self.current_signal,
            'take_profit': self.current_take_profit,
            'stop_loss': self.current_stop_loss,
            'ready_for_signals': len(self.historical_data) >= self.min_data_points
        } 
    
    def load_strategy_from_file(self, strategy_path: str) -> StrategyFunction:
        """
        Load a strategy function from a Python file
        
        Args:
            strategy_path: Path to strategy.py file
            
        Returns:
            The apply_strategy function from the file
        """
        try:
            spec = importlib.util.spec_from_file_location("strategy", strategy_path)
            strategy_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(strategy_module)
            
            if hasattr(strategy_module, 'apply_strategy'):
                return strategy_module.apply_strategy
            else:
                raise AttributeError("Strategy file must contain 'apply_strategy' function")
                
        except Exception as e:
            raise ImportError(f"Failed to load strategy from {strategy_path}: {e}")