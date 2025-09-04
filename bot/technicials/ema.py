import pandas as pd

def EMA(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the Exponential Moving Average (EMA).
    
    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        period (int): Number of periods for EMA calculation.

    Returns:
        pd.DataFrame: Original df with a new 'EMA' column.
    """
    df['EMA'] = df['Close'].ewm(span=period, adjust=False).mean()
    
    return df


def EMA_multi(df: pd.DataFrame, periods: list = [12, 26, 50]) -> pd.DataFrame:
    """
    Calculate multiple Exponential Moving Averages (EMA) with different periods.
    
    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        periods (list): List of periods for EMA calculations.

    Returns:
        pd.DataFrame: Original df with new EMA columns (e.g., 'EMA_12', 'EMA_26', etc.).
    """
    for period in periods:
        df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()
    
    return df
