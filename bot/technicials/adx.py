import pandas as pd
import numpy as np

def ADX(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the Average Directional Index (ADX) along with +DI and -DI.

    Parameters:
        df (pd.DataFrame): DataFrame with 'High', 'Low', and 'Close' columns.
        period (int): Number of periods to calculate ADX.

    Returns:
        pd.DataFrame: Original df with 'ADX', '+DI', and '-DI' columns added.
    """
    high = df['High']
    low = df['Low']
    close = df['Close']

    # True Range
    df['TR'] = np.maximum(high - low, 
                    np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))

    # Directional Movement
    df['+DM'] = np.where((high - high.shift(1)) > (low.shift(1) - low), 
                         np.maximum(high - high.shift(1), 0), 0)
    df['-DM'] = np.where((low.shift(1) - low) > (high - high.shift(1)), 
                         np.maximum(low.shift(1) - low, 0), 0)

    # Smoothed TR, +DM, -DM
    tr_smooth = df['TR'].rolling(window=period).sum()
    plus_dm_smooth = df['+DM'].rolling(window=period).sum()
    minus_dm_smooth = df['-DM'].rolling(window=period).sum()

    # +DI and -DI
    df['+DI'] = 100 * (plus_dm_smooth / tr_smooth)
    df['-DI'] = 100 * (minus_dm_smooth / tr_smooth)

    # DX and ADX
    df['DX'] = 100 * (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']))
    df['ADX'] = df['DX'].rolling(window=period).mean()

    return df.drop(columns=['TR', '+DM', '-DM', 'DX'])  # Keep only relevant outputs
