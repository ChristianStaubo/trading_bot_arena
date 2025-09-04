import pandas as pd

def RSI(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Calculate the Relative Strength Index (RSI).
    
    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        window (int): Number of periods for RSI calculation.

    Returns:
        pd.DataFrame: Original df with a new 'RSI' column.
    """
    delta = df['Close'].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    return df
