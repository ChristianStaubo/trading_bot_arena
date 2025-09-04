# This is broken, ignore for now
import pandas as pd

def is_tweezer_tops(df, tolerance: float = 0.002) -> pd.Series:
    """
    Detect tweezer tops pattern - two consecutive candles with nearly identical highs.
    
    Parameters:
        df (pd.DataFrame): OHLCV data
        tolerance (float): Maximum difference between highs as percentage of price (default 0.2%)
    
    Returns:
        pd.Series: Boolean series indicating tweezer tops pattern
    """
    
    # Calculate previous candle values
    prev_high = df['High'].shift(1)
    prev_low = df['Low'].shift(1)
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    
    # Current candle values
    curr_high = df['High']
    curr_low = df['Low']
    curr_open = df['Open']
    curr_close = df['Close']
    
    # Calculate the difference between highs
    high_diff = (curr_high - prev_high).abs()
    avg_high = (curr_high + prev_high) / 2
    
    # Calculate candle ranges and body characteristics
    prev_range = prev_high - prev_low
    curr_range = curr_high - curr_low
    
    # Calculate body sizes
    prev_body = (prev_close - prev_open).abs()
    curr_body = (curr_close - curr_open).abs()
    
    # Calculate body tops (max of open/close)
    prev_body_top = prev_open.combine(prev_close, max)
    curr_body_top = curr_open.combine(curr_close, max)
    
    # Calculate where body top sits relative to candle range
    prev_body_top_pct = (prev_body_top - prev_low) / prev_range
    curr_body_top_pct = (curr_body_top - curr_low) / curr_range
    
    return (
        # Highs are nearly identical (within tolerance)
        (high_diff / avg_high <= tolerance) &
        
        # Both candles should have meaningful range (not flat)
        (prev_range > avg_high * 0.001) &
        (curr_range > avg_high * 0.001) &
        
        # Body must be at least 15% of candle range
        (prev_body / prev_range >= 0.15) &
        (curr_body / curr_range >= 0.15) &
        
        # Body top should be no more than 40% of candle (large upper wick)
        (prev_body_top_pct <= 0.40) &
        (curr_body_top_pct <= 0.40) &
        
        # Ensure we have valid data
        (prev_high.notna()) &
        (curr_high.notna()) &
        (prev_range > 0) &
        (curr_range > 0)
    )


def is_tweezer_bottoms(df, tolerance: float = 0.002) -> pd.Series:
    """
    Detect tweezer bottoms pattern - two consecutive candles with nearly identical lows.
    
    Parameters:
        df (pd.DataFrame): OHLCV data
        tolerance (float): Maximum difference between lows as percentage of price (default 0.2%)
    
    Returns:
        pd.Series: Boolean series indicating tweezer bottoms pattern
    """
    
    # Calculate previous candle values
    prev_high = df['High'].shift(1)
    prev_low = df['Low'].shift(1)
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    
    # Current candle values
    curr_high = df['High']
    curr_low = df['Low']
    curr_open = df['Open']
    curr_close = df['Close']
    
    # Calculate the difference between lows
    low_diff = (curr_low - prev_low).abs()
    avg_low = (curr_low + prev_low) / 2
    
    # Calculate meaningful candle ranges
    prev_range = prev_high - prev_low
    curr_range = curr_high - curr_low
    
    return (
        # Lows are nearly identical (within tolerance)
        (low_diff / avg_low <= tolerance) &
        
        # Both candles should have meaningful range (not doji-like)
        (prev_range > avg_low * 0.001) &
        (curr_range > avg_low * 0.001) &
        
        # Lows should be the prominent feature (lower wicks not too small)
        (prev_low < prev_open.combine(prev_close, min)) &
        (curr_low < curr_open.combine(curr_close, min)) &
        
        # Ensure we have valid data
        (prev_low.notna()) &
        (curr_low.notna())
    )


def is_tweezer_pattern(df, tolerance: float = 0.002) -> pd.Series:
    """Detect any tweezer pattern (tops or bottoms)."""
    return is_tweezer_tops(df, tolerance) | is_tweezer_bottoms(df, tolerance) 