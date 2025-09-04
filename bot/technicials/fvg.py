"""
Fair Value Gap (FVG) Technical Indicator

A Fair Value Gap represents an area of inefficient price discovery where the market
moved so quickly that it left behind unfilled orders. These gaps often act as 
support/resistance zones that price returns to "fill".

Bullish FVG: When candle 1 low > candle 3 high (gap up)
Bearish FVG: When candle 1 high < candle 3 low (gap down)
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any


def FVG(df: pd.DataFrame, 
        min_gap_size: float = 0.0,
        max_lookback: int = 500,
        fill_threshold: float = 0.5) -> pd.DataFrame:
    """
    Add Fair Value Gap (FVG) detection to a DataFrame.
    
    Args:
        df: DataFrame with OHLC data
        min_gap_size: Minimum gap size to consider (in price points)
        max_lookback: Maximum number of candles to track open FVGs
        fill_threshold: What percentage of gap must be filled to consider it closed (0.5 = 50%)
        
    Returns:
        DataFrame with FVG columns added:
        - FVG_Bullish_Top: Top of bullish FVG zones
        - FVG_Bullish_Bottom: Bottom of bullish FVG zones  
        - FVG_Bearish_Top: Top of bearish FVG zones
        - FVG_Bearish_Bottom: Bottom of bearish FVG zones
        - FVG_Bullish_Active: Boolean for active bullish FVGs
        - FVG_Bearish_Active: Boolean for active bearish FVGs
        - FVG_Signal: 1 for new bullish FVG, -1 for new bearish FVG, 0 for none
    """
    if len(df) < 3:
        raise ValueError("DataFrame must have at least 3 rows to detect FVGs")
    
    # Validate required columns
    required_columns = ['Open', 'High', 'Low', 'Close']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    result_df = df.copy()
    
    # Initialize FVG columns
    result_df['FVG_Bullish_Top'] = np.nan
    result_df['FVG_Bullish_Bottom'] = np.nan
    result_df['FVG_Bearish_Top'] = np.nan
    result_df['FVG_Bearish_Bottom'] = np.nan
    result_df['FVG_Bullish_Active'] = False
    result_df['FVG_Bearish_Active'] = False
    result_df['FVG_Signal'] = 0
    
    # Track active FVGs
    active_bullish_fvgs = []  # List of (start_idx, top, bottom)
    active_bearish_fvgs = []  # List of (start_idx, top, bottom)
    
    # Process each candle starting from index 2 (need previous 2 candles)
    for i in range(2, len(result_df)):
        current_high = result_df.iloc[i]['High']
        current_low = result_df.iloc[i]['Low']
        
        # Get the three consecutive candles for FVG detection
        candle_1 = result_df.iloc[i-2]  # First candle
        candle_2 = result_df.iloc[i-1]  # Middle candle  
        candle_3 = result_df.iloc[i]    # Current candle
        
        # Detect Bullish FVG: candle_1_low > candle_3_high
        if candle_1['Low'] > candle_3['High']:
            gap_top = candle_1['Low']
            gap_bottom = candle_3['High']
            gap_size = gap_top - gap_bottom
            
            if gap_size >= min_gap_size:
                # New Bullish FVG detected
                active_bullish_fvgs.append((i, gap_top, gap_bottom))
                result_df.iloc[i, result_df.columns.get_loc('FVG_Signal')] = 1
                result_df.iloc[i, result_df.columns.get_loc('FVG_Bullish_Top')] = gap_top
                result_df.iloc[i, result_df.columns.get_loc('FVG_Bullish_Bottom')] = gap_bottom
        
        # Detect Bearish FVG: candle_1_high < candle_3_low  
        elif candle_1['High'] < candle_3['Low']:
            gap_top = candle_3['Low']
            gap_bottom = candle_1['High']
            gap_size = gap_top - gap_bottom
            
            if gap_size >= min_gap_size:
                # New Bearish FVG detected
                active_bearish_fvgs.append((i, gap_top, gap_bottom))
                result_df.iloc[i, result_df.columns.get_loc('FVG_Signal')] = -1
                result_df.iloc[i, result_df.columns.get_loc('FVG_Bearish_Top')] = gap_top
                result_df.iloc[i, result_df.columns.get_loc('FVG_Bearish_Bottom')] = gap_bottom
        
        # Check if any active FVGs have been filled
        active_bullish_fvgs = _check_fvg_fills(
            active_bullish_fvgs, current_high, current_low, fill_threshold, 'bullish', max_lookback, i
        )
        active_bearish_fvgs = _check_fvg_fills(
            active_bearish_fvgs, current_high, current_low, fill_threshold, 'bearish', max_lookback, i
        )
        
        # Mark active FVGs
        if active_bullish_fvgs:
            result_df.iloc[i, result_df.columns.get_loc('FVG_Bullish_Active')] = True
        if active_bearish_fvgs:
            result_df.iloc[i, result_df.columns.get_loc('FVG_Bearish_Active')] = True
    
    return result_df


def _check_fvg_fills(active_fvgs: list, 
                    current_high: float, 
                    current_low: float,
                    fill_threshold: float,
                    fvg_type: str,
                    max_lookback: int,
                    current_index: int) -> list:
    """
    Check if any active FVGs have been filled and remove them from the active list.
    
    Args:
        active_fvgs: List of active FVGs (start_idx, top, bottom)
        current_high: Current candle high
        current_low: Current candle low
        fill_threshold: Percentage of gap that must be filled
        fvg_type: 'bullish' or 'bearish'
        max_lookback: Maximum lookback period
        current_index: Current candle index
        
    Returns:
        Updated list of active FVGs with filled ones removed
    """
    remaining_fvgs = []
    
    for start_idx, gap_top, gap_bottom in active_fvgs:
        # Remove old FVGs that exceed max lookback
        if current_index - start_idx > max_lookback:
            continue
            
        gap_size = gap_top - gap_bottom
        fill_required = gap_size * fill_threshold
        
        if fvg_type == 'bullish':
            # Bullish FVG is filled when price moves down into the gap
            if current_low <= gap_bottom + fill_required:
                continue  # FVG is filled, remove it
        else:  # bearish
            # Bearish FVG is filled when price moves up into the gap
            if current_high >= gap_top - fill_required:
                continue  # FVG is filled, remove it
        
        # FVG is still active
        remaining_fvgs.append((start_idx, gap_top, gap_bottom))
    
    return remaining_fvgs


def get_nearest_fvg_zones(df: pd.DataFrame, 
                         current_price: float,
                         max_distance: Optional[float] = None,
                         zone_count: int = 3) -> Dict[str, Any]:
    """
    Get the nearest FVG zones above and below current price.
    
    Args:
        df: DataFrame with FVG data
        current_price: Current market price
        max_distance: Maximum distance to consider zones (None for no limit)
        zone_count: Maximum number of zones to return in each direction
        
    Returns:
        Dictionary with nearest FVG zones:
        {
            'bullish_zones': [(top, bottom, distance), ...],
            'bearish_zones': [(top, bottom, distance), ...],
            'nearest_support': float or None,
            'nearest_resistance': float or None
        }
    """
    # Get all FVG zones that have been detected
    fvg_data = df.dropna(subset=['FVG_Bullish_Top', 'FVG_Bearish_Top'], how='all')
    
    bullish_zones = []
    bearish_zones = []
    
    for _, row in fvg_data.iterrows():
        if not pd.isna(row['FVG_Bullish_Top']):
            top = row['FVG_Bullish_Top']
            bottom = row['FVG_Bullish_Bottom']
            distance = min(abs(current_price - top), abs(current_price - bottom))
            
            if max_distance is None or distance <= max_distance:
                bullish_zones.append((top, bottom, distance))
        
        if not pd.isna(row['FVG_Bearish_Top']):
            top = row['FVG_Bearish_Top']
            bottom = row['FVG_Bearish_Bottom']
            distance = min(abs(current_price - top), abs(current_price - bottom))
            
            if max_distance is None or distance <= max_distance:
                bearish_zones.append((top, bottom, distance))
    
    # Sort by distance and limit count
    bullish_zones.sort(key=lambda x: x[2])
    bearish_zones.sort(key=lambda x: x[2])
    
    bullish_zones = bullish_zones[:zone_count]
    bearish_zones = bearish_zones[:zone_count]
    
    # Find nearest support and resistance
    nearest_support = None
    nearest_resistance = None
    
    for top, bottom, _ in bullish_zones + bearish_zones:
        # Support: zones below current price
        if top < current_price:
            if nearest_support is None or top > nearest_support:
                nearest_support = top
        # Resistance: zones above current price  
        if bottom > current_price:
            if nearest_resistance is None or bottom < nearest_resistance:
                nearest_resistance = bottom
    
    return {
        'bullish_zones': bullish_zones,
        'bearish_zones': bearish_zones,
        'nearest_support': nearest_support,
        'nearest_resistance': nearest_resistance
    }


def fvg_trading_signals(df: pd.DataFrame,
                       entry_mode: str = 'retest',
                       min_gap_size: float = 2.0,
                       risk_reward_ratio: float = 2.0) -> pd.DataFrame:
    """
    Generate trading signals based on FVG zones.
    
    Args:
        df: DataFrame with FVG data
        entry_mode: 'retest' (enter on return to FVG) or 'breakout' (enter on FVG creation)
        min_gap_size: Minimum gap size for signal generation
        risk_reward_ratio: Risk to reward ratio for targets
        
    Returns:
        DataFrame with FVG trading signals:
        - FVG_Trade_Signal: 1 for long, -1 for short, 0 for none
        - FVG_Entry_Price: Suggested entry price
        - FVG_Stop_Loss: Suggested stop loss
        - FVG_Take_Profit: Suggested take profit
    """
    result_df = df.copy()
    
    # Initialize trading columns
    result_df['FVG_Trade_Signal'] = 0
    result_df['FVG_Entry_Price'] = np.nan
    result_df['FVG_Stop_Loss'] = np.nan
    result_df['FVG_Take_Profit'] = np.nan
    
    for i in range(len(result_df)):
        row = result_df.iloc[i]
        
        if entry_mode == 'breakout':
            # Enter immediately when new FVG is detected
            if row['FVG_Signal'] == 1:  # Bullish FVG
                gap_size = row['FVG_Bullish_Top'] - row['FVG_Bullish_Bottom']
                if gap_size >= min_gap_size:
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Trade_Signal')] = 1
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Entry_Price')] = row['Close']
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Stop_Loss')] = row['FVG_Bullish_Bottom']
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Take_Profit')] = row['Close'] + (gap_size * risk_reward_ratio)
            
            elif row['FVG_Signal'] == -1:  # Bearish FVG
                gap_size = row['FVG_Bearish_Top'] - row['FVG_Bearish_Bottom']
                if gap_size >= min_gap_size:
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Trade_Signal')] = -1
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Entry_Price')] = row['Close']
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Stop_Loss')] = row['FVG_Bearish_Top']
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Take_Profit')] = row['Close'] - (gap_size * risk_reward_ratio)
        
        elif entry_mode == 'retest':
            # Enter when price returns to test an FVG zone
            current_high = row['High']
            current_low = row['Low']
            
            # Check for bullish retest (price returning to bullish FVG from above)
            if row['FVG_Bullish_Active'] and not pd.isna(row['FVG_Bullish_Top']):
                fvg_top = row['FVG_Bullish_Top']
                fvg_bottom = row['FVG_Bullish_Bottom']
                gap_size = fvg_top - fvg_bottom
                
                # Price touching the FVG zone from above
                if current_low <= fvg_top and current_high >= fvg_bottom and gap_size >= min_gap_size:
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Trade_Signal')] = 1
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Entry_Price')] = fvg_top
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Stop_Loss')] = fvg_bottom
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Take_Profit')] = fvg_top + (gap_size * risk_reward_ratio)
            
            # Check for bearish retest (price returning to bearish FVG from below)
            elif row['FVG_Bearish_Active'] and not pd.isna(row['FVG_Bearish_Top']):
                fvg_top = row['FVG_Bearish_Top']
                fvg_bottom = row['FVG_Bearish_Bottom']
                gap_size = fvg_top - fvg_bottom
                
                # Price touching the FVG zone from below
                if current_high >= fvg_bottom and current_low <= fvg_top and gap_size >= min_gap_size:
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Trade_Signal')] = -1
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Entry_Price')] = fvg_bottom
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Stop_Loss')] = fvg_top
                    result_df.iloc[i, result_df.columns.get_loc('FVG_Take_Profit')] = fvg_bottom - (gap_size * risk_reward_ratio)
    
    return result_df


def print_fvg_summary(df: pd.DataFrame) -> None:
    """
    Print a summary of FVG detection results.
    
    Args:
        df: DataFrame with FVG data
    """
    # Count FVGs
    total_bullish = df['FVG_Signal'].eq(1).sum()
    total_bearish = df['FVG_Signal'].eq(-1).sum()
    total_fvgs = total_bullish + total_bearish
    
    # Get current active FVGs
    current_active_bullish = df['FVG_Bullish_Active'].iloc[-1] if len(df) > 0 else False
    current_active_bearish = df['FVG_Bearish_Active'].iloc[-1] if len(df) > 0 else False
    
    # Calculate average gap sizes
    bullish_gaps = df.dropna(subset=['FVG_Bullish_Top'])
    bearish_gaps = df.dropna(subset=['FVG_Bearish_Top'])
    
    avg_bullish_gap = (bullish_gaps['FVG_Bullish_Top'] - bullish_gaps['FVG_Bullish_Bottom']).mean() if len(bullish_gaps) > 0 else 0
    avg_bearish_gap = (bearish_gaps['FVG_Bearish_Top'] - bearish_gaps['FVG_Bearish_Bottom']).mean() if len(bearish_gaps) > 0 else 0
    
    print("📊 FAIR VALUE GAP (FVG) SUMMARY")
    print("=" * 50)
    print(f"🟢 Bullish FVGs Detected: {total_bullish}")
    print(f"🔴 Bearish FVGs Detected: {total_bearish}")
    print(f"📈 Total FVGs: {total_fvgs}")
    print(f"⚡ Average Bullish Gap Size: {avg_bullish_gap:.2f}")
    print(f"⚡ Average Bearish Gap Size: {avg_bearish_gap:.2f}")
    print(f"🎯 Currently Active:")
    print(f"   • Bullish FVGs: {'Yes' if current_active_bullish else 'No'}")
    print(f"   • Bearish FVGs: {'Yes' if current_active_bearish else 'No'}")
    
    if total_fvgs > 0:
        print(f"📊 FVG Frequency: {len(df) / total_fvgs:.1f} candles per FVG")
    
    print("=" * 50)


# Example usage and testing
if __name__ == "__main__":
    # Create sample data for testing
    
    # Generate sample OHLC data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='H')
    
    # Create trending price data with some gaps
    base_price = 4000
    price_changes = np.random.normal(0, 5, 100)
    price_changes[20:23] = [15, 20, 10]  # Create a gap up
    price_changes[60:63] = [-15, -25, -10]  # Create a gap down
    
    prices = np.cumsum(price_changes) + base_price
    
    # Create OHLC from base prices
    df_test = pd.DataFrame({
        'timestamp': dates,
        'Open': prices + np.random.normal(0, 1, 100),
        'High': prices + np.abs(np.random.normal(2, 1, 100)),
        'Low': prices - np.abs(np.random.normal(2, 1, 100)),
        'Close': prices + np.random.normal(0, 1, 100),
        'Volume': np.random.randint(1000, 10000, 100)
    })
    
    # Apply FVG indicator
    df_with_fvg = FVG(df_test, min_gap_size=5.0)
    
    # Add trading signals
    df_with_signals = fvg_trading_signals(df_with_fvg, entry_mode='retest', min_gap_size=5.0)
    
    # Print summary
    print_fvg_summary(df_with_signals)
    
    # Show first few FVGs detected
    fvg_signals = df_with_signals[df_with_signals['FVG_Signal'] != 0]
    if len(fvg_signals) > 0:
        print(f"\n🎯 DETECTED FVGs:")
        for _, row in fvg_signals.head().iterrows():
            signal_type = "Bullish" if row['FVG_Signal'] == 1 else "Bearish"
            if row['FVG_Signal'] == 1:
                gap_size = row['FVG_Bullish_Top'] - row['FVG_Bullish_Bottom']
                print(f"   {signal_type} FVG: {row['FVG_Bullish_Bottom']:.2f} - {row['FVG_Bullish_Top']:.2f} (Gap: {gap_size:.2f})")
            else:
                gap_size = row['FVG_Bearish_Top'] - row['FVG_Bearish_Bottom']
                print(f"   {signal_type} FVG: {row['FVG_Bearish_Bottom']:.2f} - {row['FVG_Bearish_Top']:.2f} (Gap: {gap_size:.2f})")
    
    print(f"\n✅ FVG Indicator test completed successfully!")
