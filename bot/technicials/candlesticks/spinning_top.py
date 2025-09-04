import pandas as pd

def is_spinning_top(df) -> pd.Series:
    """Detect spinning top candlestick patterns with small body and long symmetrical wicks."""

    body = (df['Close'] - df['Open']).abs()
    candle_range = df['High'] - df['Low']
    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)

    # Prevent divide-by-zero
    body = body.replace(0, 1e-10)
    candle_range = candle_range.replace(0, 1e-10)

    return (
        # Small body (less than 25% of total candle range)
        (body < (candle_range * 0.25)) &
        
        # Both wicks are relatively long (at least 1.5x body size)
        (upper_wick > body * 1.5) &
        (lower_wick > body * 1.5) &
        
        # Wicks are somewhat symmetrical (neither is more than 3x the other)
        (upper_wick / lower_wick < 2) &
        (lower_wick / upper_wick < 2)
    )
