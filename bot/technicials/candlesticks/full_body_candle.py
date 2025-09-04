import pandas as pd

def is_full_body_candle(df, body_threshold: float = 0.95) -> pd.Series:
    """Detect full body candles where the body takes up most of the candle range."""

    body = (df['Close'] - df['Open']).abs()
    candle_range = df['High'] - df['Low']
    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)

    # Prevent divide-by-zero
    candle_range = candle_range.replace(0, 1e-10)

    return (
        # Body takes up at least 95% of the total candle range
        (body / candle_range >= body_threshold) &
        
        # Minimal wicks (each wick < 5% of candle range)
        (upper_wick / candle_range <= (1 - body_threshold)) &
        (lower_wick / candle_range <= (1 - body_threshold)) &
        
        # Ensure we have some meaningful range (not a flat line)
        (candle_range > 0.1)
    )


def is_bullish_full_body(df, body_threshold: float = 0.95) -> pd.Series:
    """Detect bullish full body candles (close > open)."""
    return is_full_body_candle(df, body_threshold) & (df['Close'] > df['Open'])


def is_bearish_full_body(df, body_threshold: float = 0.95) -> pd.Series:
    """Detect bearish full body candles (close < open)."""
    return is_full_body_candle(df, body_threshold) & (df['Close'] < df['Open'])
