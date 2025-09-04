# Trading Strategies

This directory contains organized trading strategies as Python modules. Each strategy is self-contained with its trading logic and optional order cancellation rules.

## 📁 Structure

```
strategies/
├── __init__.py                          # Strategies module with helper functions
├── README.md                            # This file
└── bollinger_bands/                     # Example strategy module
    ├── __init__.py                      # Strategy metadata and configuration
    ├── strategy.py                      # Main trading logic (REQUIRED)
    └── cancel_order_strategy.py         # Order cancellation logic (OPTIONAL)
```

## 🚀 Usage

### Method 1: Using Helper Function (Recommended)

```python
from strategies import get_strategy_path

strategy_name = "bollinger_bands"
bot = Bot(
    symbol="EURUSD",
    strategy_name=strategy_name,
    strategy_path=get_strategy_path(strategy_name, "strategy"),
    cancel_strategy_path=get_strategy_path(strategy_name, "cancel_order_strategy"),  # Optional
    # ... other parameters
)
```

### Method 2: Direct Paths

```python
bot = Bot(
    symbol="EURUSD",
    strategy_name="bollinger_bands",
    strategy_path="strategies/bollinger_bands/strategy.py",
    cancel_strategy_path="strategies/bollinger_bands/cancel_order_strategy.py",  # Optional
    # ... other parameters
)
```

## 📋 Available Strategies

### 1. **bollinger_bands** ✅ COMPLETED

**Description:** Bollinger Bands breakout/reversal strategy with ATR-based risk management

**Files:**

- `strategy.py` - Main entry/exit logic using Bollinger Bands + RSI
- `cancel_order_strategy.py` - 5-second timeout + custom cancellation rules

**Indicators Used:** Bollinger Bands, RSI, ATR

**Default Parameters:**

- BB Window: 20 periods
- BB Std Dev: 2.0
- RSI Window: 14 periods
- ATR Window: 14 periods
- Cancel Timeout: 5 seconds

## 🔧 Creating New Strategies

To add a new strategy (e.g., `macd_crossover`):

### 1. Create Strategy Directory

```bash
mkdir strategies/macd_crossover
```

### 2. Create Required Files

#### `strategies/macd_crossover/__init__.py`

```python
"""
MACD Crossover Strategy
"""

STRATEGY_NAME = "macd_crossover"
STRATEGY_VERSION = "1.0.0"
STRATEGY_DESCRIPTION = "MACD signal line crossover strategy"

DEFAULT_PARAMS = {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    # ... other parameters
}

REQUIRED_INDICATORS = ["macd"]
```

#### `strategies/macd_crossover/strategy.py` (REQUIRED)

```python
def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply MACD crossover strategy

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with signals added
    """
    # Add MACD indicator
    # Generate signals
    # Add TP/SL levels
    return df
```

#### `strategies/macd_crossover/cancel_order_strategy.py` (OPTIONAL)

```python
from datetime import datetime
from ib_async import Ticker, Trade

def should_cancel_order(ticker: Ticker, trade: Trade, order_time: datetime) -> bool:
    """Custom cancellation logic for MACD strategy"""
    return False
```

### 3. Register Strategy

Add to `strategies/__init__.py`:

```python
AVAILABLE_STRATEGIES = [
    "bollinger_bands",
    "macd_crossover",  # Add your new strategy
]
```

### 4. Use Strategy

```python
strategy_name = "macd_crossover"
bot = Bot(
    strategy_name=strategy_name,
    strategy_path=get_strategy_path(strategy_name, "strategy"),
    cancel_strategy_path=get_strategy_path(strategy_name, "cancel_order_strategy"),  # Optional
    # ... other parameters
)
```

## 🎯 Strategy Requirements

### Required Functions

#### `strategy.py`

- ✅ **`apply_strategy(df: pd.DataFrame) -> pd.DataFrame`** - Main trading logic

#### `cancel_order_strategy.py` (Optional)

- ✅ **`should_cancel_order(ticker: Ticker, trade: Trade, order_time: datetime) -> bool`** - Cancellation logic

### DataFrame Requirements

Your `apply_strategy` function must return a DataFrame with these columns:

- ✅ **`Trade_Signal`** - Signal type (`OPEN_LONG`, `OPEN_SHORT`, `CLOSE_POSITION`, `NONE`)
- ✅ **`Take_Profit`** - Take profit price (when signal present)
- ✅ **`Stop_Loss`** - Stop loss price (when signal present)

### Optional Columns

- `Signal_Strength` - Confidence level (0.0 to 1.0)
- `Entry_Price` - Suggested entry price
- Any custom indicator columns for debugging

## 🔍 Strategy Testing

Each strategy should be testable with historical data:

```python
import pandas as pd
from strategies.bollinger_bands.strategy import apply_strategy

# Load historical data
df = pd.read_csv("historical_data.csv")

# Test strategy
result = apply_strategy(df)
print(result[['Trade_Signal', 'Take_Profit', 'Stop_Loss']].tail())
```

## 📊 Best Practices

1. **Modular Design** - Keep strategies self-contained
2. **Clear Documentation** - Document strategy logic and parameters
3. **Error Handling** - Handle edge cases gracefully
4. **Backtesting** - Test strategies with historical data first
5. **Parameter Tuning** - Make key parameters configurable
6. **Resource Efficiency** - Optimize for real-time performance

## 🚀 Next Steps

- [ ] Add more strategies (MACD, RSI, EMA crossovers)
- [ ] Create strategy backtesting framework
- [ ] Add parameter optimization tools
- [ ] Implement multi-timeframe strategies
- [ ] Add risk management enhancements
