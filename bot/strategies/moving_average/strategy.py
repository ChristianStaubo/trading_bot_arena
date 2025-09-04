import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

import pandas as pd
import numpy as np
from technicials.tema import TEMA_multi
from technicials.cmo import CMO
from technicials.adx import ADX
from technicials.atr import ATR


def generate_trade_signals(df):
    """
    Generate trade signals for Triple TEMA strategy.
    
    Criteria for a trade:
        - Long:
            - TEMA_10 > TEMA_80 (main timeframe)
            - ADX > 40 (trend strength)
            - CMO > 40 (momentum)
        - Short:
            - TEMA_10 < TEMA_80 (main timeframe)
            - ADX > 40 (trend strength) 
            - CMO < -40 (momentum)
    
    Note: This is a single-timeframe version. For multi-timeframe,
    use apply_triple_tema_strategy_multi_tf function.
    """
    # Initialize signal column
    df['Trade_Signal'] = 0
    
    # Long conditions
    long_conditions = (
        (df['TEMA_10'] > df['TEMA_80']) &
        (df['ADX'] > 40) &
        (df['CMO'] > 40)
    )
    
    # Short conditions  
    short_conditions = (
        (df['TEMA_10'] < df['TEMA_80']) &
        (df['ADX'] > 40) &
        (df['CMO'] < -40)
    )
    
    # Apply signals
    df.loc[long_conditions, 'Trade_Signal'] = 1
    df.loc[short_conditions, 'Trade_Signal'] = -1
    
    return df


def apply_take_profit(row):
    """
    Apply take profit to the current row.
    Entry: Close price
    TP: 4x ATR distance from entry
    """
    if row['Trade_Signal'] == 1:  # Long
        return row['Close'] + (4.0 * row['ATR'])
    elif row['Trade_Signal'] == -1:  # Short
        return row['Close'] - (4.0 * row['ATR'])
    else:
        return 0.0


def apply_stop_loss(row):
    """
    Apply stop loss to the current row.
    SL is 3x ATR distance from entry price.
    """
    if row['Trade_Signal'] == 1:  # Long
        return row['Close'] - (3.0 * row['ATR'])  # SL below entry
    elif row['Trade_Signal'] == -1:  # Short
        return row['Close'] + (3.0 * row['ATR'])  # SL above entry
    else:
        return 0.0


def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the Triple TEMA strategy to a DataFrame.
    
    This function is designed to work with the MultiprocessBacktester.
    
    Args:
        df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
        
    Returns:
        DataFrame with Trade_Signal, Take_Profit, Stop_Loss columns added
    """
    # Make a copy to avoid modifying the original
    df_strategy = df.copy()
    
    # Reset index to integer for backtester compatibility
    df_strategy.reset_index(drop=True, inplace=True)
    
    # Add technical indicators
    df_strategy = TEMA_multi(df_strategy, periods=[10, 80])
    df_strategy = CMO(df_strategy, 14)
    df_strategy = ADX(df_strategy, 14)
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


def apply_triple_tema_strategy_multi_tf(df_30min: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the Triple TEMA multi-timeframe strategy.
    
    Args:
        df_30min: 30-minute DataFrame with OHLCV data
        df_4h: 4-hour DataFrame with OHLCV data
        
    Returns:
        DataFrame with Trade_Signal, Take_Profit, Stop_Loss columns added
    """
    # Prepare 30-minute data
    df_30min_strategy = df_30min.copy()
    df_30min_strategy.reset_index(drop=True, inplace=True)
    
    # Prepare 4-hour data  
    df_4h_strategy = df_4h.copy()
    df_4h_strategy.reset_index(drop=True, inplace=True)
    
    # Add indicators to 30-minute data
    df_30min_strategy = TEMA_multi(df_30min_strategy, periods=[10, 80])
    df_30min_strategy = CMO(df_30min_strategy, 14)
    df_30min_strategy = ADX(df_30min_strategy, 14)
    df_30min_strategy = ATR(df_30min_strategy)
    
    # Add indicators to 4-hour data
    df_4h_strategy = TEMA_multi(df_4h_strategy, periods=[20, 70])
    
    # Drop TR column if it exists
    if 'TR' in df_30min_strategy.columns:
        df_30min_strategy.drop(columns=['TR'], inplace=True)
    
    # Drop missing values
    df_30min_strategy.dropna(inplace=True)
    df_4h_strategy.dropna(inplace=True)
    
    # For multi-timeframe analysis, we'll use a simplified approach:
    # Check the overall 4h trend and apply it as a filter
    
    # Get the latest 4h TEMA condition
    latest_4h_bullish = df_4h_strategy['TEMA_20'].iloc[-1] > df_4h_strategy['TEMA_70'].iloc[-1]
    latest_4h_bearish = df_4h_strategy['TEMA_20'].iloc[-1] < df_4h_strategy['TEMA_70'].iloc[-1]
    
    # Initialize signal column
    df_30min_strategy['Trade_Signal'] = 0
    
    # Long conditions (30min signals + 4h trend filter)
    long_conditions = (
        (df_30min_strategy['TEMA_10'] > df_30min_strategy['TEMA_80']) &
        (df_30min_strategy['ADX'] > 40) &
        (df_30min_strategy['CMO'] > 40) &
        latest_4h_bullish  # 4h trend filter
    )
    
    # Short conditions (30min signals + 4h trend filter)
    short_conditions = (
        (df_30min_strategy['TEMA_10'] < df_30min_strategy['TEMA_80']) &
        (df_30min_strategy['ADX'] > 40) &
        (df_30min_strategy['CMO'] < -40) &
        latest_4h_bearish  # 4h trend filter
    )
    
    # Apply signals
    df_30min_strategy.loc[long_conditions, 'Trade_Signal'] = 1
    df_30min_strategy.loc[short_conditions, 'Trade_Signal'] = -1
    
    # Apply take profit and stop loss
    df_30min_strategy['Take_Profit'] = df_30min_strategy.apply(apply_take_profit, axis=1)
    df_30min_strategy['Stop_Loss'] = df_30min_strategy.apply(apply_stop_loss, axis=1)
    
    return df_30min_strategy


# Unit test to see if the strategy is working
if __name__ == "__main__":
    print("🧪 Testing Triple TEMA Strategy")
    print("=" * 50)
    
    # Load ES data
    csv_path = '../../es_data/1_min/2024/2024_1_min.csv'
    df_raw = pd.read_csv(csv_path)
    
    # Convert timestamp and prepare data
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'], utc=True)
    df_raw.set_index('timestamp', inplace=True)
    df_raw.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    df_raw.dropna(inplace=True)
    
    # Resample to 30 min candles
    df = df_raw.resample('30min').agg({
        'Open': 'first',
        'High': 'max', 
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    df.dropna(inplace=True)
    
    # Test with a subset of data
    df_test = df.iloc[:1000].copy()
    
    print(f"Loaded {len(df_test)} 30-minute candles")
    
    # Apply the strategy
    df_strategy = apply_strategy(df_test)
    
    # Print results
    long_signals = (df_strategy['Trade_Signal'] == 1).sum()
    short_signals = (df_strategy['Trade_Signal'] == -1).sum()
    total_signals = long_signals + short_signals
    
    print(f"Number of long signals: {long_signals}")
    print(f"Number of short signals: {short_signals}")
    print(f"Total signals: {total_signals}")
    print(f"Signal frequency: {total_signals/len(df_strategy)*100:.2f}%")
    
    if total_signals > 0:
        print("\n✅ Strategy is generating signals!")
        print(f"First few signals:")
        signals_df = df_strategy[df_strategy['Trade_Signal'] != 0][['Close', 'Trade_Signal', 'TEMA_10', 'TEMA_80', 'ADX', 'CMO']].head()
        print(signals_df)
    else:
        print("\n⚠️  No signals generated. Consider adjusting parameters.")
        
        # Debug information
        tema_10_over_80 = (df_strategy['TEMA_10'] > df_strategy['TEMA_80']).sum()
        adx_over_40 = (df_strategy['ADX'] > 40).sum()
        cmo_over_40 = (df_strategy['CMO'] > 40).sum()
        cmo_under_neg40 = (df_strategy['CMO'] < -40).sum()
        
        print(f"\nCondition Analysis:")
        print(f"TEMA 10 > 80: {tema_10_over_80}/{len(df_strategy)} ({tema_10_over_80/len(df_strategy)*100:.1f}%)")
        print(f"ADX > 40: {adx_over_40}/{len(df_strategy)} ({adx_over_40/len(df_strategy)*100:.1f}%)")
        print(f"CMO > 40: {cmo_over_40}/{len(df_strategy)} ({cmo_over_40/len(df_strategy)*100:.1f}%)")
        print(f"CMO < -40: {cmo_under_neg40}/{len(df_strategy)} ({cmo_under_neg40/len(df_strategy)*100:.1f}%)")
