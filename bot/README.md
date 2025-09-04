# Trading Bot Architecture

A modular multithreading trading bot system. Each bot instance is designed to handle a single strategy and trading pair

## Managers

### 1. **managers/ibkr_helper_manager/**

**Structure:**

- `main.py` - Core IBKR connection and contract management
- `types.py` - IBKR-specific type definitions
- `utils.py` - Helper functions for contract creation

**Responsibilities:**

- Handles all IBKR-specific operations and connections
- Creates and qualifies contracts (uses `ContFuture` for ES futures)
- Manages real-time data subscriptions (bars + ticker data)
- **Conditional ticker subscriptions** for order monitoring
- Clean callback interface for Bot to subscribe to events
- Passes raw IBKR bar data to Bot (no data conversion)
- **Type-safe ticker management** using native `ib_async.Ticker` objects

### 2. **managers/logging_manager/**

**Structure:**

- `main.py` - Centralized logging setup and management
- `types.py` - Logging configuration types
- `utils.py` - Log formatting and utility functions

**Responsibilities:**

- Creates main bot logger + per-instrument loggers automatically
- Settings-driven logger creation based on active trading pairs
- Structured logging methods for different event types:
  - `log_new_candle()` - Clean candle data logging
  - `log_strategy_state()` - Technical indicators and signals
  - `log_connection_event()` - IBKR connection events
  - `log_strategy_initialization()` - Strategy setup details

### 3. **managers/trade_decision_manager/**

**Structure:**

- `main.py` - Pure signal generation and strategy logic
- `types.py` - TradeSignal, CandleResult type definitions
- `utils.py` - Strategy loading and data processing utilities

**Responsibilities:**

- **Pure signal generation and strategy logic**
- Loads strategy functions from `strategy.py` files
- Maintains rolling historical data window for single symbol
- Applies strategy on every new candle
- **Returns trade decisions without position awareness**:
  - Signal generation and detection (`OPEN_LONG`, `OPEN_SHORT`, `CLOSE_POSITION`, `NONE`)
  - Take profit and stop loss levels
  - Signal confidence and strength
  - No IBKR knowledge or position tracking

### 4. **managers/order_manager/**

**Structure:**

- `main.py` - Core order execution and position management
- `types.py` - OrderInfo, Position, and order-related type definitions
- `utils.py` - Order management utilities and helpers

**Responsibilities:**

- **Complete order execution and position management for single symbol**
- Tracks live orders and positions for this bot's symbol
- **Configurable order management rules** from bot configuration:
  - Cancel orders if price moves X ticks from limit
  - Order timeout handling
  - Emergency position flattening
  - Symbol-specific risk rules
- **Order execution**:
  - OCO (One-Cancels-Other) limit orders with TP/SL
  - Order state tracking and monitoring
  - Failsafe logic for missed executions
- Integrates with type-safe `order_management.py` utilities

### 5. **Bot Class**

**Single-Strategy Focus:**

- Each bot instance handles **one strategy + one symbol + one set of order rules**
- Clean orchestrator - minimal and readable
- Loads strategy from `strategy.py` using `TradeDecisionManager.load_strategy_from_file()`
- **Optional cancel strategy** loaded from `cancel_order_strategy.py`
- **Simple decision → execution flow**:
  1. Get trade decision from TradeDecisionManager
  2. Execute trades via OrderManager if signal present
  3. **Conditionally monitor orders** with real-time ticker data
  4. **Auto-cancel orders** based on custom cancellation logic
- Type-safe with `CandleResult` and `TradeSignal` return types

**Order Monitoring Features:**

- ✅ **Real-time ticker subscriptions** - Only when orders are active
- ✅ **Custom cancellation logic** - Define rules in `cancel_order_strategy.py`
- ✅ **Automatic cleanup** - Stops monitoring when orders fill/cancel
- ✅ **Resource efficient** - No unnecessary market data subscriptions

## 🏗️ Single-Bot Architecture

```python
# Each bot instance is focused and simple
class Bot:
    def __init__(self, client_id: int, symbol: str, strategy: str, order_rules: dict):
        # One symbol, one strategy, one set of rules
        self.symbol = symbol
        self.trade_decision_manager = TradeDecisionManager(symbol, strategy)
        self.order_manager = OrderManager(symbol, order_rules)

    def onNewCandle(self, symbol: str, bar):
        # 1. Convert & log candle data
        bar_data = {...}
        self.logging_manager.log_new_candle(symbol, bar_data)

        # 2. Get pure trading decision (no position knowledge)
        result: CandleResult = self.trade_decision_manager.process_new_candle(bar_data)

        # 3. Execute trades based on decision
        if result.trade_signal:
            self.order_manager.place_order(symbol, result.trade_signal)

        # 4. Manage existing orders using this bot's specific rules
        self.order_manager.analyze_current_orders(symbol, current_price=result.current_price)

# Deploy multiple bots for different strategies
bots = [
    Bot(client_id=1, symbol="ES", strategy="bollinger_bands",
        cancel_strategy="cancel_order_strategy.py", order_rules={...}),  # With cancellation
    Bot(client_id=2, symbol="EURUSD", strategy="macd", order_rules={...}),  # No cancellation
    Bot(client_id=3, symbol="NQ", strategy="scalping",
        cancel_strategy="aggressive_cancel.py", order_rules={...}),  # Custom cancellation
]
```

**TradeDecisionManager.process_new_candle()** internally:

1. Updates strategy signals using the `strategy.py`
2. Returns clean trade decision with TP/SL levels
3. No position tracking or IBKR knowledge

**OrderManager** handles:

1. Order placement (OCO limit orders)
2. Position and order state tracking for this symbol
3. Order management rules (cancellation, timeouts)
4. Emergency position management

## 📋 Strategy Pattern Implementation

✅ **Achieved the target pattern**: Define strategy in `strategy.py`, each bot loads it automatically

```python
# strategy.py
def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    # Add technical indicators
    df = BollingerBands(df, window=20, std_dev=3.5)
    df = RSI(df, window=14)
    df = ATR(df)

    # Generate trade signals
    df = generate_trade_signals(df)

    # Add TP/SL levels
    df['Take_Profit'] = df.apply(apply_take_profit, axis=1)
    df['Stop_Loss'] = df.apply(apply_stop_loss, axis=1)

    return df
```

Each bot automatically loads this strategy and applies it to its specific symbol!

## 📋 Order Cancellation Strategy Pattern ✅ OPTIONAL

**NEW**: Define custom order cancellation logic that monitors orders in real-time:

```python
# cancel_order_strategy.py (OPTIONAL)
from datetime import datetime
from ib_async import Ticker, Trade

def should_cancel_order(ticker: Ticker, trade: Trade, order_time: datetime) -> bool:
    """
    Custom cancellation logic using real-time market data

    Args:
        ticker: Real-time market data from IBKR
        trade: Order/trade object from IBKR
        order_time: When the order was placed

    Returns:
        True if order should be cancelled
    """
    # Example: Cancel if 5 seconds elapsed and order still pending
    if (datetime.now() - order_time).total_seconds() > 5:
        if trade.orderStatus.status in ['Submitted', 'PreSubmitted', 'PendingSubmit']:
            if trade.orderStatus.remaining > 0:
                return True

    # Add your custom logic here:
    # - Price movement thresholds
    # - Time-based rules
    # - Market condition checks
    # - Volatility-based cancellation

    return False
```

**How it works:**

1. 🔄 **Order placed** → Bot starts ticker subscription automatically
2. 📡 **Real-time updates** → `should_cancel_order()` called with live data
3. ✅ **Order fills/cancels** → Ticker subscription automatically stopped
4. 🧹 **Clean resource management** → No lingering subscriptions

**Benefits:**

- ⚡ **Responsive order management** - React to market changes in real-time
- 💰 **Resource efficient** - Only subscribes when orders are active
- 🎯 **Strategy-specific** - Each bot can have different cancellation rules
- 🔒 **Type-safe** - Uses native IBKR `Ticker` and `Trade` objects
- 🔧 **Completely optional** - Works without cancellation strategy

Each bot can optionally load a cancellation strategy for advanced order management

## 📋 Bot Configuration

**Each bot gets its own configuration file:**

```json
// bot_bollinger_es.json
{
  "client_id": 1,
  "strategy_name": "bollinger_bands",
  "symbol": "ES",
  "exchange": "CME",
  "timeframe": "5min",
  "cancel_strategy": "cancel_order_strategy.py",  // OPTIONAL
  "order_rules": {
    "cancel_order_if_price_moves": 5,
    "order_timeout_minutes": 30,
    "max_slippage_ticks": 2,
    "default_quantity": 1
  }
}

// bot_macd_eurusd.json
{
  "client_id": 2,
  "strategy_name": "macd",
  "symbol": "EURUSD",
  "exchange": "IDEALPRO",
  "timeframe": "5min",
  "order_rules": {
    "cancel_order_if_price_moves": 10,
    "order_timeout_minutes": 60,
    "max_slippage_ticks": 3,
    "default_quantity": 1000
  }
}
```

## Design Decisions

### **Single-Strategy-Per-Bot Architecture**

Each bot handles one strategy because:

- **Reliability**: Strategy failures are isolated
- **Simplicity**: No complex routing or shared state
- **Scalability**: Easy horizontal scaling across machines
- **Clarity**: Each bot has a single, clear purpose
- **IBKR Support**: Multiple client connections are explicitly supported

### **Clean Separation of Decision vs Execution**

We separated trade decisions from order execution because:

- **TradeDecisionManager** can be easily tested with historical data
- **OrderManager** handles complex IBKR order mechanics separately
- Strategy logic stays pure and broker-agnostic
- Order management rules can be configured per bot
- Each component has a single, clear responsibility

### **Manager Folder Structure**

Each manager is organized as a package because:

- **main.py**: Core functionality and public interface
- **types.py**: Type definitions and data classes
- **utils.py**: Helper functions and utilities
- **Better maintainability**: Related code is grouped together
- **Clear imports**: `from managers.order_manager.main import OrderManager`
- **Type safety**: Centralized type definitions per manager

## 📋 Still To Do

### 3. **Enhanced Features** 🔄 FUTURE

- Multi-timeframe analysis within strategies
- Advanced risk management (position sizing, portfolio limits)
- Real-time web dashboard for monitoring multiple bots
- Strategy performance comparison across bots
