import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from technicials.bollinger_bands import BollingerBands
from technicials.atr import ATR
from technicials.rsi import RSI


def generate_trade_signals(df):
    """
    Criteria for a trade:
        - Long:
            - Price closed below BB_Lower and the BB_Width is greater than 3 ATR 
        - Short:
            - Price closed above BB_Upper and the BB_Width is greater than 3 ATR
    
    """
    # Initialize signal column
    df['Trade_Signal'] = 0
    
    # Long conditions
    long_conditions = (
        (df['Close'] < df['BB_Lower'])
    )
    
    # Short conditions  
    short_conditions = (
        (df['Close'] > df['BB_Upper'])
    )
    
    # Apply signals
    df.loc[long_conditions, 'Trade_Signal'] = 1
    df.loc[short_conditions, 'Trade_Signal'] = -1
    
    
    
    
    return df




def apply_take_profit(row):
    """
    Apply take profit to the current row.
    Entry: Close price
    SL: 1.5x ATR distance from entry
    TP: 2x the risk distance (2:1 reward-to-risk ratio)
    """
    if row['Trade_Signal'] == 1:  # Long
        # Entry = Close, SL = Close - (1.5 * ATR)
        risk_distance = 1.5 * row['ATR']
        return row['Close'] + (2.0 * risk_distance)  # 2:1 reward-to-risk
    elif row['Trade_Signal'] == -1:  # Short
        # Entry = Close, SL = Close + (1.5 * ATR)
        risk_distance = 1.5 * row['ATR']
        return row['Close'] - (2.0 * risk_distance)  # 2:1 reward-to-risk
    else:
        return 0.0

def apply_stop_loss(row):
    """
    Apply stop loss to the current row.
    SL is 2x ATR distance from entry price.
    """
    if row['Trade_Signal'] == 1:  # Long
        return row['Close'] - (1.5 * row['ATR'])  # SL below entry
    elif row['Trade_Signal'] == -1:  # Short
        return row['Close'] + (1.5 * row['ATR'])  # SL above entry
    else:
        return 0.0




def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the Bollinger Band strategy to a DataFrame.
    
    This function is designed to work with the MultiprocessBacktester.
    
    Args:
        df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
        
    Returns:
        DataFrame with Trade_Signal, Take_Profit, Stop_Loss columns added
    """
    # Make a copy to avoid modifying the original
    df_strategy = df.copy()
    
    # Add technical indicators
    # TODO: Load parameters from settings.json
    df_strategy = BollingerBands(df_strategy, window=20, std_dev=1)
    df_strategy = RSI(df_strategy, window=14)
    df_strategy = ATR(df_strategy)
    
    # Drop the TR column if it exists
    if 'TR' in df_strategy.columns:
        df_strategy.drop(columns=['TR'], inplace=True)
    
    # Drop any missing values
    df_strategy.dropna(inplace=True)
    
    # Generate trade signals
    df_strategy = generate_trade_signals(df_strategy)
    
    # Apply take profit and stop loss
    df_strategy['Take_Profit'] = df_strategy.apply(apply_take_profit, axis=1)
    df_strategy['Stop_Loss'] = df_strategy.apply(apply_stop_loss, axis=1)
    
    return df_strategy

# Unit test to see if the strategy is working
if __name__ == "__main__":
    # Original testing code (only runs when script is executed directly)
    # Load ES data
    csv_1min_path = '../../es_data/1_min/2023/2023_1_min.csv'
    df = pd.read_csv(csv_1min_path)

    # Convert timestamp and prepare data
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.set_index('timestamp', inplace=True)
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    df.dropna(inplace=True)

    # Resample to 5 min candles
    df = df.resample('5min').agg({
        'Open': 'first',
        'High': 'max', 
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    df.dropna(inplace=True)

    print(f"Loaded {len(df)} total 5-minute candles")

    # Apply the strategy
    df_test = apply_strategy(df)
    
    # Print results
    print(f"Number of long signals: {df_test[df_test['Trade_Signal'] == 1].shape[0]}")
    print(f"Number of short signals: {df_test[df_test['Trade_Signal'] == -1].shape[0]}")
    print(f"Number of trades: {df_test[df_test['Trade_Signal'] != 0].shape[0]}")

