import pandas as pd

def is_small_body_lower_wick(df) -> pd.Series:
    """Detect candles shaped like a hammer or hanging man based on geometry."""

    body = (df['Close'] - df['Open']).abs()

    candle_range = df['High'] - df['Low']

    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']

    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)

    # 5️⃣ Prevent divide-by-zero or weird logic if body = 0 (doji)
    # Replace 0 with a very small number so conditions like (lower_wick > body * 2) still work
    body = body.replace(0, 1e-10)

    # 6️⃣ Return a Series of booleans where:
    return (
        # ✅ Candle has a small real body (less than 30% of total candle range)
        (body < (candle_range * 0.3)) &

        # ✅ Lower wick is at least 2x the body height (strong shadow)
        (lower_wick > body * 2) &

        # ✅ Upper wick is tiny: less than 15% of body height (clean hammer shape)
        (upper_wick < body * 0.15)
    )




def is_hanging_man(df) -> pd.Series:
    """Detect hanging man shape + uptrend context."""
    pattern = is_small_body_lower_wick(df)
    uptrend = df['Close'] > df['Close'].shift(3)
    return pattern & uptrend

def is_hammer(df) -> pd.Series:
    """Detect hammer shape + downtrend context."""
    pattern = is_small_body_lower_wick(df)
    downtrend = df['Close'] < df['Close'].shift(3)
    return pattern & downtrend
