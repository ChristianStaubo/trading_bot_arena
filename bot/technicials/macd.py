import pandas as pd

def MACD(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    """
    Calculate the Moving Average Convergence Divergence (MACD).
    
    MACD is a trend-following momentum indicator that shows the relationship between two moving averages.
    
    Parameters:
        df (pd.DataFrame): DataFrame with a 'Close' column.
        fast_period (int): Number of periods for the fast EMA (default: 12).
        slow_period (int): Number of periods for the slow EMA (default: 26).
        signal_period (int): Number of periods for the signal line EMA (default: 9).

    Returns:
        pd.DataFrame: Original df with new columns:
            - 'MACD_Line': The main MACD line (fast EMA - slow EMA)
            - 'MACD_Signal': The signal line (EMA of MACD line)
            - 'MACD_Histogram': The histogram (MACD line - signal line)
    """
    # Calculate the fast and slow EMAs
    fast_ema = df['Close'].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df['Close'].ewm(span=slow_period, adjust=False).mean()
    
    # Calculate the MACD line
    df['MACD_Line'] = fast_ema - slow_ema
    
    # Calculate the signal line (EMA of MACD line)
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=signal_period, adjust=False).mean()
    
    # Calculate the histogram
    df['MACD_Histogram'] = df['MACD_Line'] - df['MACD_Signal']
    
    return df


def MACD_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate MACD trading signals based on line crossovers.
    
    Requires MACD to be calculated first using MACD() function.
    
    Parameters:
        df (pd.DataFrame): DataFrame with MACD columns already calculated.

    Returns:
        pd.DataFrame: Original df with new signal columns:
            - 'MACD_Bullish_Crossover': 1 when MACD line crosses above signal line
            - 'MACD_Bearish_Crossover': 1 when MACD line crosses below signal line
            - 'MACD_Above_Zero': 1 when MACD line is above zero line
            - 'MACD_Below_Zero': 1 when MACD line is below zero line
    """
    # Ensure MACD columns exist
    required_columns = ['MACD_Line', 'MACD_Signal']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found. Please run MACD() function first.")
    
    # Calculate crossover signals
    df['MACD_Bullish_Crossover'] = ((df['MACD_Line'] > df['MACD_Signal']) & 
                                    (df['MACD_Line'].shift(1) <= df['MACD_Signal'].shift(1))).astype(int)
    
    df['MACD_Bearish_Crossover'] = ((df['MACD_Line'] < df['MACD_Signal']) & 
                                    (df['MACD_Line'].shift(1) >= df['MACD_Signal'].shift(1))).astype(int)
    
    # Calculate zero line crossovers
    df['MACD_Above_Zero'] = (df['MACD_Line'] > 0).astype(int)
    df['MACD_Below_Zero'] = (df['MACD_Line'] < 0).astype(int)
    
    return df
