"""
Bollinger Bands Trading Strategy

A complete trading strategy implementation using Bollinger Bands with:
- Entry signals based on Bollinger Band breakouts/reversals
- Stop loss and take profit calculation
- Optional order cancellation logic

Files:
- strategy.py: Main trading logic for entry/exit signals
- cancel_order_strategy.py: Custom order cancellation rules
"""

# Strategy metadata
STRATEGY_NAME = "bollinger_bands"
STRATEGY_VERSION = "1.0.0"
STRATEGY_DESCRIPTION = "Bollinger Bands breakout/reversal strategy with ATR-based risk management"

# Default parameters
DEFAULT_PARAMS = {
    "bb_window": 20,
    "bb_std_dev": 2.0,
    "rsi_window": 14,
    "atr_window": 14,
    "atr_multiplier": 1.5,
    "cancel_timeout_seconds": 5
}

# Required technical indicators
REQUIRED_INDICATORS = [
    "bollinger_bands",
    "rsi", 
    "atr"
] 