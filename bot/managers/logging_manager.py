import sys
import os
import logging

from ib_async import BarData
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
from typing import Dict, List, Optional
from lib.config.settings_models import BotSettings
from lib.utils.logging import TradingBotLogger

# Logtail integration
try:
    from logtail import LogtailHandler
except ImportError:
    LogtailHandler = None
    print("Warning: logtail package not installed. Bot logs will only go to files and console.")


class CombinedLogger:
    """
    Logger that combines file logging and logtail logging
    """
    def __init__(self, file_logger, logtail_logger):
        self.file_logger = file_logger
        self.logtail_logger = logtail_logger
    
    def info(self, message):
        self.file_logger.info(message)
        if self.logtail_logger:
            self.logtail_logger.info(message)
    
    def error(self, message):
        self.file_logger.error(message)
        if self.logtail_logger:
            self.logtail_logger.error(message)
    
    def warning(self, message):
        self.file_logger.warning(message)
        if self.logtail_logger:
            self.logtail_logger.warning(message)
    
    def debug(self, message):
        self.file_logger.debug(message)
        if self.logtail_logger:
            self.logtail_logger.debug(message)


class LoggingManager:
    """
    Centralized logging management for the trading bot.
    
    Handles creation and management of:
    - Main bot logger
    - Per-instrument loggers  
    - Manager-specific loggers (future: candle_manager, technicals_manager)
    """
    
    def __init__(self, symbol: str = None, strategy_name: str = "trading_bot", version: str = "1.0.0"):
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.version = version
        
        # Logger storage
        self._main_logger: Optional[TradingBotLogger] = None
        self._instrument_loggers: Dict[str, TradingBotLogger] = {}
        self._manager_loggers: Dict[str, TradingBotLogger] = {}
        self._logtail_logger = None
        self._combined_logger = None
        
        # Initialize loggers
        self._setup_main_logger()
        self._setup_logtail_logger()
        self._setup_combined_logger()
        
        # Initialize instrument logger if symbol provided
        if self.symbol:
            self._setup_instrument_logger(self.symbol)
    
    def _setup_main_logger(self):
        """Setup the main bot logger"""
        self._main_logger = TradingBotLogger("main.log")
        self._main_logger.info("🚀 LoggingManager initialized")
        self._main_logger.info(f"📋 Strategy: {self.strategy_name}")
        self._main_logger.info(f"📋 Version: {self.version}")
    
    def _setup_logtail_logger(self):
        """Setup logtail logging for remote log aggregation"""
        # Get environment variables
        source_token = os.getenv('LOGTAIL_SOURCE_TOKEN')
        host = os.getenv('LOGTAIL_HOST')
        
        print(f"LoggingManager - Token: {source_token[:8] if source_token else 'None'}...")
        print(f"LoggingManager - Host: {host}")
        
        # Create logger
        logger = logging.getLogger("bot")
        logger.handlers = []  # Clear existing handlers
        logger.setLevel(logging.DEBUG)  # Set minimal log level
        
        # Create handlers
        if source_token and host and LogtailHandler:
            # Logtail handler
            logtail_handler = LogtailHandler(source_token=source_token, host=host)
            logger.addHandler(logtail_handler)
            print("✅ Logtail handler added successfully!")
        else:
            missing = []
            if not source_token:
                missing.append("LOGTAIL_SOURCE_TOKEN")
            if not host:
                missing.append("LOGTAIL_HOST")
            if not LogtailHandler:
                missing.append("logtail package")
            print(f"❌ Missing logtail config: {', '.join(missing)}")
        
        # Console handler for local development (always add this)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - BOT - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        logger.propagate = False
        
        if source_token and host and LogtailHandler:
            print("✅ Console handler added for local development!")
            self._logtail_logger = logger
        else:
            print("⚠️ Logtail disabled - using file and console logging only")
            self._logtail_logger = None
    
    def _setup_combined_logger(self):
        """Setup combined logger that logs to both file and logtail"""
        self._combined_logger = CombinedLogger(self._main_logger, self._logtail_logger)
        self._combined_logger.info("✅ Combined logging (files + logtail) initialized")
    
    def _setup_instrument_logger(self, symbol: str):
        """Create logger for a single trading symbol"""
        log_filename = f"{symbol}.log"
        
        # Create dedicated logger for this instrument
        instrument_logger = TradingBotLogger(log_filename)
        self._instrument_loggers[symbol] = instrument_logger
        
        # Log initial setup to both main and instrument loggers
        self._main_logger.info(f"📋 Created logger for {symbol}: {log_filename}")
        instrument_logger.info(f"🎯 {symbol} logger initialized")
        instrument_logger.info(f"   Strategy: {self.strategy_name}")
        instrument_logger.info(f"   Version: {self.version}")
    
    def _get_active_trading_pairs(self) -> List[str]:
        """Extract all active trading pair symbols from settings"""
        active_pairs = []
        
        # Add active forex pairs
        for pair in self.settings.trading_pairs.forex:
            if pair.active:
                active_pairs.append(pair.symbol)
        
        # Add active stock pairs  
        for pair in self.settings.trading_pairs.stocks:
            if pair.active:
                active_pairs.append(pair.symbol)
        
        # Add active futures pairs
        for pair in self.settings.trading_pairs.futures:
            if pair.active:
                active_pairs.append(pair.symbol)
        
        return active_pairs
    
    def get_main_logger(self) -> TradingBotLogger:
        """Get the main bot logger"""
        if not self._main_logger:
            raise RuntimeError("Main logger not initialized")
        return self._main_logger
    
    def get_combined_logger(self) -> CombinedLogger:
        """Get the combined logger that logs to both file and logtail"""
        if not self._combined_logger:
            raise RuntimeError("Combined logger not initialized")
        return self._combined_logger
    
    def is_logtail_enabled(self) -> bool:
        """Check if logtail integration is enabled"""
        return self._logtail_logger is not None
    
    def get_logtail_status(self) -> str:
        """Get a human-readable status of logtail integration"""
        source_token = os.getenv('LOGTAIL_SOURCE_TOKEN')
        host = os.getenv('LOGTAIL_HOST')
        
        if source_token and host and LogtailHandler:
            return "✅ Enabled"
        else:
            return "❌ Disabled (missing env vars or package)"
    
    def get_instrument_logger(self, symbol: str) -> Optional[TradingBotLogger]:
        """
        Get the logger for a specific instrument
        
        Args:
            symbol: Trading symbol (e.g., 'ES', 'EURUSD', 'AAPL')
            
        Returns:
            TradingBotLogger for the symbol, or None if not found
        """
        return self._instrument_loggers.get(symbol)
    
    def get_manager_logger(self, manager_name: str) -> TradingBotLogger:
        """
        Get or create a logger for a specific manager
        
        Args:
            manager_name: Name of the manager (e.g., 'candle_manager', 'technicals_manager')
            
        Returns:
            EnhancedTradingBotLogger for the manager
        """
        if manager_name not in self._manager_loggers:
            log_filename = f"{manager_name}.log"
            self._manager_loggers[manager_name] = TradingBotLogger(log_filename)
            self._main_logger.info(f"📋 Created manager logger: {log_filename}")
        
        return self._manager_loggers[manager_name]
    
    def log_new_candle(self, symbol: str, bar_data: BarData):
        """
        Log a new candle to the appropriate instrument logger
        
        Args:
            symbol: Trading symbol
            bar_data: Dictionary containing OHLCV data
        """
        instrument_logger = self.get_instrument_logger(symbol)
        if not instrument_logger:
            self._main_logger.warning(f"⚠️ No logger found for {symbol}")
            return
        
        # Log detailed candle information
        instrument_logger.info(f"📊 NEW CANDLE RECEIVED")
        instrument_logger.info(f"   Symbol: {symbol}")
        instrument_logger.info(f"   Time: {bar_data.date}")
        instrument_logger.info(f"   Open: ${bar_data.open}")
        instrument_logger.info(f"   High: ${bar_data.high}")
        instrument_logger.info(f"   Low: ${bar_data.low}")
        instrument_logger.info(f"   Close: ${bar_data.close}")
        instrument_logger.info(f"   Volume: {bar_data.volume}")
    
    def log_strategy_state(self, symbol: str, strategy_data: dict):
        """
        Log strategy/technical analysis state to instrument logger
        
        Args:
            symbol: Trading symbol
            strategy_data: Dictionary containing strategy indicators and signals
        """
        instrument_logger = self.get_instrument_logger(symbol)
        if not instrument_logger:
            return
        
        timeframe = strategy_data.get('timeframe', 'Unknown')
        instrument_logger.info(f"🎯 STRATEGY STATE ({timeframe})")
        
        # Log technical indicators if present
        if 'indicators' in strategy_data:
            indicators = strategy_data['indicators']
            
            # Bollinger Bands
            if 'BB_Upper' in indicators:
                instrument_logger.info(f"   📈 Bollinger Bands:")
                instrument_logger.info(f"      Upper: ${indicators['BB_Upper']:.2f}")
                instrument_logger.info(f"      SMA:   ${indicators.get('SMA', 0):.2f}")
                instrument_logger.info(f"      Lower: ${indicators['BB_Lower']:.2f}")
                instrument_logger.info(f"      Width: ${indicators.get('BB_Width', 0):.2f}")
            
            # RSI
            if 'RSI' in indicators:
                rsi_value = indicators['RSI']
                rsi_status = "🔴 Overbought" if rsi_value > 70 else "🟢 Oversold" if rsi_value < 30 else "⚪ Neutral"
                instrument_logger.info(f"   📊 RSI: {rsi_value:.1f} ({rsi_status})")
            
            # ATR
            if 'ATR' in indicators:
                instrument_logger.info(f"   📏 ATR: ${indicators['ATR']:.2f}")
        
        # Log signals
        signal = strategy_data.get('signal', 0)
        signal_text = "🟢 LONG" if signal == 1 else "🔴 SHORT" if signal == -1 else "⚪ NO SIGNAL"
        instrument_logger.info(f"   🎯 Signal: {signal_text}")
        
        # Log signal strength if present
        if 'strength' in strategy_data and signal != 0:
            strength = strategy_data['strength']
            instrument_logger.info(f"   💪 Strength: {strength.get('strength', 0)}/3 ({strength.get('confidence', 'unknown')})")
            
            # Log strong signals to main logger too
            if strength.get('confidence') in ['medium', 'high']:
                self._main_logger.info(f"🚨 STRONG {signal_text} SIGNAL for {symbol} (confidence: {strength.get('confidence')})")
    
    def log_connection_event(self, event_type: str, details: str = ""):
        """
        Log connection events to main logger
        
        Args:
            event_type: 'connected', 'disconnected', 'error'
            details: Additional details about the event
        """
        if event_type == "connected":
            self._main_logger.info(f"🔗 IBKR connection established {details}")
        elif event_type == "disconnected":
            self._main_logger.warning(f"🔌 IBKR connection lost {details}")
        elif event_type == "error":
            self._main_logger.error(f"❌ IBKR connection error: {details}")
    
    def log_strategy_initialization(self, symbol: str, details: dict):
        """
        Log strategy initialization to both main and instrument loggers
        
        Args:
            symbol: Trading symbol
            details: Dictionary with initialization details
        """
        instrument_logger = self.get_instrument_logger(symbol)
        
        # Log to main logger
        self._main_logger.info(f"✅ {symbol} strategy initialized")
        
        # Log detailed info to instrument logger
        if instrument_logger:
            instrument_logger.info(f"🚀 {symbol} STRATEGY INITIALIZED")
            instrument_logger.info(f"   Asset Type: {details.get('asset_type', 'Unknown')}")
            instrument_logger.info(f"   Exchange: {details.get('exchange', 'Unknown')}")
            instrument_logger.info(f"   Timeframe: {details.get('timeframe', 'Unknown')}")
            instrument_logger.info(f"   Strategy: {details.get('strategy', 'Unknown')}")
            instrument_logger.info(f"   Historical Data: {details.get('historical_bars', 0)} candles")
    
    def get_active_instruments(self) -> List[str]:
        """Get list of active instruments with loggers"""
        return list(self._instrument_loggers.keys())
    
    def cleanup(self):
        """Clean up logging resources if needed"""
        self._main_logger.info("🧹 LoggingManager cleanup complete")
        # Note: TradingBotLogger handles its own cleanup automatically 