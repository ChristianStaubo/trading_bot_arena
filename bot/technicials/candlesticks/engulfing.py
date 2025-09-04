import pandas as pd

def is_bullish_engulfing(df) -> pd.Series:
    """Detect bullish engulfing patterns where current candle engulfs previous bearish candle."""
    
    # Calculate previous candle values
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    prev_high = df['High'].shift(1)
    prev_low = df['Low'].shift(1)
    
    # Current candle values
    curr_open = df['Open']
    curr_close = df['Close']
    curr_high = df['High']
    curr_low = df['Low']
    
    # Calculate body sizes
    prev_body = (prev_close - prev_open).abs()
    curr_body = (curr_close - curr_open).abs()
    
    return (
        # Previous candle is bearish
        (prev_close < prev_open) &
        
        # Current candle is bullish
        (curr_close > curr_open) &
        
        # Current candle's body engulfs previous candle's body
        (curr_open <= prev_close) &
        (curr_close >= prev_open) &
        
        # Current candle should be meaningful size (not tiny)
        (curr_body > prev_body * 0.5) &
        
        # Ensure we have valid data (not first candle)
        (prev_open.notna()) &
        (prev_close.notna())
    )


def is_bearish_engulfing(df) -> pd.Series:
    """Detect bearish engulfing patterns where current candle engulfs previous bullish candle."""
    
    # Calculate previous candle values
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    prev_high = df['High'].shift(1)
    prev_low = df['Low'].shift(1)
    
    # Current candle values
    curr_open = df['Open']
    curr_close = df['Close']
    curr_high = df['High']
    curr_low = df['Low']
    
    # Calculate body sizes
    prev_body = (prev_close - prev_open).abs()
    curr_body = (curr_close - curr_open).abs()
    
    return (
        # Previous candle is bullish
        (prev_close > prev_open) &
        
        # Current candle is bearish
        (curr_close < curr_open) &
        
        # Current candle's body engulfs previous candle's body
        (curr_open >= prev_close) &
        (curr_close <= prev_open) &
        
        # Current candle should be meaningful size (not tiny)
        (curr_body > prev_body * 0.5) &
        
        # Ensure we have valid data (not first candle)
        (prev_open.notna()) &
        (prev_close.notna())
    )


def is_engulfing(df) -> pd.Series:
    """Detect any engulfing pattern (bullish or bearish)."""
    return is_bullish_engulfing(df) | is_bearish_engulfing(df) 