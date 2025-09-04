import pandas as pd
import numpy as np

def DojiPattern(df: pd.DataFrame, tolerance: float = 0.001) -> pd.DataFrame:
    """
    Detect Doji candlestick patterns.
    
    A Doji occurs when the open and close prices are virtually the same,
    indicating indecision in the market.
    
    Parameters:
        df (pd.DataFrame): DataFrame with OHLCV data
        tolerance (float): Tolerance for open/close difference as ratio of range
    
    Returns:
        pd.DataFrame: DataFrame with 'Doji' column added (True/False)
    """
    
    # Calculate the body size (difference between open and close)
    body_size = abs(df['Close'] - df['Open'])
    
    # Calculate the total range (high - low)
    total_range = df['High'] - df['Low']
    
    # Avoid division by zero
    total_range = total_range.replace(0, np.nan)
    
    # Doji condition: body size is very small relative to the total range
    doji_condition = (body_size / total_range) <= tolerance
    
    # Add the Doji column
    df['Doji'] = doji_condition.fillna(False)
    
    return df


def DojiStrength(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Doji strength (how close to perfect doji).
    
    Parameters:
        df (pd.DataFrame): DataFrame with OHLCV data
    
    Returns:
        pd.DataFrame: DataFrame with 'Doji_Strength' column added (0-1)
    """
    
    body_size = abs(df['Close'] - df['Open'])
    total_range = df['High'] - df['Low']
    
    # Avoid division by zero
    total_range = total_range.replace(0, np.nan)
    
    # Strength is inverse of body ratio (1 = perfect doji, 0 = no doji)
    doji_strength = 1 - (body_size / total_range)
    
    # Clamp between 0 and 1
    doji_strength = doji_strength.clip(0, 1)
    
    df['Doji_Strength'] = doji_strength.fillna(0)
    
    return df 