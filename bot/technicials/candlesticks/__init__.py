# Candlestick Patterns Subpackage
"""
Candlestick pattern recognition functions.

This subpackage contains various candlestick pattern detection algorithms
for technical analysis.
"""

# Import available patterns
from .doji import DojiPattern, DojiStrength
from .engulfing import is_bullish_engulfing, is_bearish_engulfing, is_engulfing
from .tweezer_tops import is_tweezer_tops, is_tweezer_bottoms, is_tweezer_pattern
# from .hammer import HammerPattern

__version__ = "1.0.0"

# Available patterns
__all__ = [
    'DojiPattern',
    'DojiStrength',
    'is_bullish_engulfing',
    'is_bearish_engulfing', 
    'is_engulfing',
    'is_tweezer_tops',
    'is_tweezer_bottoms',
    'is_tweezer_pattern',
    # 'HammerPattern',
]

# Convenience function for when you have multiple patterns
def detect_all_patterns(df):
    """
    Detect all available candlestick patterns in a DataFrame.
    
    Parameters:
        df (pd.DataFrame): OHLCV data
    
    Returns:
        pd.DataFrame: DataFrame with pattern columns added
    """
    # Apply available patterns
    df = DojiPattern(df)
    df = DojiStrength(df)
    df['BullishEngulfing'] = is_bullish_engulfing(df)
    df['BearishEngulfing'] = is_bearish_engulfing(df)
    df['TweezerTops'] = is_tweezer_tops(df)
    df['TweezerBottoms'] = is_tweezer_bottoms(df)
    # df = HammerPattern(df)
    return df 