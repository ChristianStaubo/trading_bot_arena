import pandas as pd
import numpy as np

def CMO(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the Chande Momentum Oscillator (CMO).
    
    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        period (int): Number of periods to calculate the CMO.

    Returns:
        pd.DataFrame: Original df with a new 'CMO' column.
    """
    delta = df['Close'].diff()

    # Gains (positive deltas) and losses (negative deltas)
    up = delta.where(delta > 0, 0)
    down = -delta.where(delta < 0, 0)

    sum_up = up.rolling(window=period).sum()
    sum_down = down.rolling(window=period).sum()

    df['CMO'] = 100 * (sum_up - sum_down) / (sum_up + sum_down)

    return df
