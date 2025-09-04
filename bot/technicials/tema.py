import pandas as pd

def TEMA(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the Triple Exponential Moving Average (TEMA).
    
    TEMA = 3 * EMA1 - 3 * EMA2 + EMA3
    where:
        EMA1 = EMA(Close, period)
        EMA2 = EMA(EMA1, period)
        EMA3 = EMA(EMA2, period)

    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        period (int): Number of periods for TEMA calculation.

    Returns:
        pd.DataFrame: Original df with a new 'TEMA' column.
    """
    ema1 = df['Close'].ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()

    df['TEMA'] = 3 * (ema1 - ema2) + ema3
    return df


def TEMA_multi(df: pd.DataFrame, periods: list = [14, 21, 50]) -> pd.DataFrame:
    """
    Calculate multiple Triple Exponential Moving Averages (TEMA) with different periods.
    
    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        periods (list): List of periods for TEMA calculations.

    Returns:
        pd.DataFrame: Original df with new TEMA columns (e.g., 'TEMA_14', 'TEMA_21', etc.).
    """
    for period in periods:
        ema1 = df['Close'].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()

        df[f'TEMA_{period}'] = 3 * (ema1 - ema2) + ema3

    return df
