import pandas as pd
from typing import Callable, Optional, Dict, List, Any, Protocol
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class TradeAction(str, Enum):
    """Trade action types"""
    OPEN_LONG = "OPEN_LONG"
    OPEN_SHORT = "OPEN_SHORT" 
    CLOSE_POSITION = "CLOSE_POSITION"
    NONE = "NONE"


class ConfidenceLevel(str, Enum):
    """Signal confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyFunction(Protocol):
    """Protocol for strategy functions that follow our standard format"""
    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Strategy function that takes OHLCV data and returns DataFrame with signals
        
        Args:
            df: DataFrame with OHLCV columns (Open, High, Low, Close, Volume)
            
        Returns:
            DataFrame with additional columns:
            - Trade_Signal (int): 1 for long, -1 for short, 0 for no signal
            - Take_Profit (float): take profit price level
            - Stop_Loss (float): stop loss price level
            - Technical indicators: BB_Upper, BB_Lower, RSI, ATR, etc.
        """
        ...


class TradeSignal(BaseModel):
    """Pure trade signal information with full type safety"""
    action: TradeAction
    entry_price: float = Field(gt=0, description="Entry price for the trade")
    take_profit: float = Field(gt=0, description="Take profit price")
    stop_loss: float = Field(gt=0, description="Stop loss price")
    confidence: ConfidenceLevel
    indicators: Dict[str, float] = Field(default_factory=dict, description="Technical indicators at signal time")
    
    class Config:
        use_enum_values = True


class StrategySignalResult(BaseModel):
    """Result from strategy signal processing with full type safety"""
    symbol: str
    old_signal: int  # Previous signal: -1, 0, 1
    new_signal: int  # New signal: -1, 0, 1
    signal_changed: bool
    take_profit: float
    stop_loss: float
    current_price: float
    indicators: Dict[str, float] = Field(default_factory=dict)
    error: Optional[str] = None


class CandleResult(BaseModel):
    """Result from processing a new candle with full type safety"""
    symbol: str
    trade_signal: Optional[TradeSignal] = None
    current_price: float = Field(gt=0)
    signal_changed: bool = False 