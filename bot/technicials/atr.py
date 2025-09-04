import pandas as pd

def ATR(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Calculate the Average True Range (ATR).
    
    Parameters:
        df (pd.DataFrame): DataFrame with columns 'High', 'Low', 'Close'.
        window (int): Rolling window size for ATR calculation.
    
    Returns:
        pd.DataFrame: Original df with 'TR' and 'ATR' columns added.
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    df['TR'] = tr
    df['ATR'] = tr.rolling(window=window, min_periods=1).mean()

    return df
