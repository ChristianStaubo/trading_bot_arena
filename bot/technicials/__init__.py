# Technical Indicators Package
# This file makes the technicials directory a Python package

# Import all main indicators for easy access
from .bollinger_bands import BollingerBands
from .atr import ATR
from .rsi import RSI
from .macd import MACD, MACD_signals

# Version info
__version__ = "1.0.0"
__author__ = "Christian"

# Expose main indicators at package level
__all__ = [
    'BollingerBands',
    'ATR', 
    'RSI',
    'MACD',
    'MACD_signals',
]

# Optional: Create convenience functions
def get_all_indicators():
    """Return list of all available indicators"""
    return __all__

def apply_all_indicators(df, **kwargs):
    """Apply all indicators to a DataFrame"""
    df = BollingerBands(df, **kwargs.get('bb_params', {}))
    df = ATR(df, **kwargs.get('atr_params', {}))
    df = RSI(df, **kwargs.get('rsi_params', {}))
    df = MACD(df, **kwargs.get('macd_params', {}))
    return df 