import sys
sys.path.append('../..')
import asyncio
from ib_async import IB, Contract, Stock, Future, Forex, ContFuture, Ticker
from dotenv import load_dotenv
import os
from typing import Dict, Callable, Optional, List
from datetime import datetime

load_dotenv()


class IbkrHelperManager:
    """
    Handles all IBKR-specific operations including connection management,
    contract creation, and real-time data subscriptions.
    
    Exposes callback interfaces for the Bot to subscribe to events.
    """
    
    def __init__(self, host: str = None, port: int = None, client_id: int = None):
        # IBKR connection parameters
        self.host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("IBKR_PORT", 7497))
        self.client_id = client_id or int(os.getenv("IBKR_CLIENT_ID", 1))
        
        # IBKR connection
        self.ib = IB()
        
        # Active contracts
        self.active_contracts: Dict[str, Contract] = {}
        
        # Keep track of ticker objects and event handlers so we can disconnect them properly
        # Only tracking what IBKR doesn't provide: our custom event handlers and exact ticker objects
        self.ticker_objects: Dict[str, Ticker] = {}  # symbol -> actual Ticker object
        self.ticker_event_handlers: Dict[str, Callable] = {}  # symbol -> event handler
        
        # Callback functions that Bot can set
        self.on_new_bar: Optional[Callable] = None
        self.on_ticker_update: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Internal state
        self._is_connected = False
    
    async def connect(self) -> bool:
        """
        Connect to IBKR TWS/Gateway async
        Returns True if successful, False otherwise
        """
        try:
            print(f"🔌 Connecting to IBKR at {self.host}:{self.port} (client_id={self.client_id})...")
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id, timeout=10)
            self._setup_event_handlers()
            self._is_connected = True
            print(f"✅ Successfully connected to IBKR")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to IBKR: {e}")
            print(f"💡 Error type: {type(e).__name__}")
            return False
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.ib.isConnected():
            self.ib.disconnect()
        self._is_connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to IBKR"""
        return self._is_connected and self.ib.isConnected()
    
    def _setup_event_handlers(self):
        """Setup IBKR event handlers"""
        self.ib.connectedEvent += self._on_ibkr_connected
        self.ib.disconnectedEvent += self._on_ibkr_disconnected
        self.ib.errorEvent += self._on_ibkr_error
    
    def _on_ibkr_connected(self):
        """Internal handler for IBKR connection established"""
        self._is_connected = True
        if self.on_connected:
            self.on_connected()
    
    def _on_ibkr_disconnected(self):
        """Internal handler for IBKR connection lost"""
        self._is_connected = False
        if self.on_disconnected:
            self.on_disconnected()
    
    def _on_ibkr_error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Internal handler for IBKR errors"""
        # Handle connection-related errors specifically
        if errorCode in [1100, 1102, 10182]:  # Connection lost/restored/failed errors
            print(f"🔴 [IBKR ERROR] {errorCode}: {errorString}")
            if self.on_error:
                try:
                    if asyncio.iscoroutinefunction(self.on_error):
                        asyncio.create_task(self.on_error(errorCode, errorString, reqId))
                    else:
                        self.on_error(errorCode, errorString, reqId)
                except Exception as e:
                    print(f"❌ Error calling error callback: {e}")

    
    async def create_and_qualify_contract(self, symbol: str, asset_type: str, exchange: str) -> Optional[Contract]:
        """
        Create and qualify an IBKR contract
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD', 'ES', 'AAPL')
            asset_type: 'forex', 'futures', or 'stocks'
            exchange: Exchange name
            
        Returns:
            Qualified contract or None if failed
        """
        try:
            # Create contract based on asset type
            asset_type_lower = asset_type.lower()  # Make case-insensitive
            if asset_type_lower == "forex":
                contract = Forex(symbol)
            elif asset_type_lower == "futures":
                if symbol == "ES":
                    # Use continuous future for ES - automatically handles front month
                    # Note: ES futures typically trade on GLOBEX exchange
                    contract = ContFuture(symbol='ES', exchange=exchange)
                    print(f"📋 Creating ES continuous future for {exchange}")
                else:
                    contract = Future(symbol=symbol, exchange=exchange)
            elif asset_type_lower == "stocks":
                contract = Stock(symbol, exchange, "USD")
            else:
                raise ValueError(f"Unknown asset type: {asset_type} (supported: forex, futures, stocks)")
            
            print(f"📋 Created contract: {contract}")
            
            # Qualify the contract
            qualified_contracts = await self.ib.qualifyContractsAsync(contract)
            
            # Process any pending IBKR events to prevent hanging
            await asyncio.sleep(0.1)
            
            if not qualified_contracts:
                print(f"❌ No qualified contracts found for {symbol}")
                return None
            
            qualified_contract = qualified_contracts[0]
            print(f"✅ Qualified contract: {qualified_contract}")
            
            # Process events again after qualification
            await asyncio.sleep(0.1)
            
            # Only add to active_contracts if we have a valid qualified contract
            if qualified_contract and hasattr(qualified_contract, 'conId') and qualified_contract.conId:
                self.active_contracts[symbol] = qualified_contract
                print(f"✅ Added {symbol} to active contracts")
                
                # Final event processing before returning
                await asyncio.sleep(0.1)
                return qualified_contract
            else:
                print(f"❌ Invalid qualified contract for {symbol}")
                return None
            
        except Exception as e:
            print(f"❌ Error creating contract for {symbol}: {e}")
            return None
    
    async def start_real_time_data(self, symbol: str, bar_size: str) -> bool:
        """
        Start real-time data subscription for a symbol
        
        Args:
            symbol: Symbol to subscribe to
            bar_size: Bar size (e.g., '1 min', '5 mins')
            
        Returns:
            True if successful, False otherwise
        """
        if symbol not in self.active_contracts:
            print(f"❌ No contract found for {symbol}")
            return False
        
        contract = self.active_contracts[symbol]
        if contract is None:
            print(f"❌ Contract for {symbol} is None")
            return False
        
        try:
            print(f"📡 Starting real-time data for {symbol} with contract: {contract}")
            
            # Determine appropriate parameters based on contract type
            if hasattr(contract, 'secType') and contract.secType == 'CASH':
                # Forex contracts - use MIDPOINT data
                what_to_show = 'MIDPOINT'
                duration_str = '2 D'  # Forex might need longer duration
                print(f"🔄 Using MIDPOINT data for forex {symbol}")
            else:
                # Futures, stocks, etc. - use TRADES data
                what_to_show = 'TRADES'
                duration_str = '1 D'
                print(f"🔄 Using TRADES data for {symbol}")
            
            # Use historical data with keepUpToDate=True for streaming bars
            bars = await self.ib.reqHistoricalDataAsync(
                contract=contract,
                endDateTime='',  # Current time
                durationStr=duration_str,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=False,  # Include after-hours data
                formatDate=1,
                keepUpToDate=True  # This enables streaming updates
            )
            
            if bars is None:
                print(f"❌ No bars returned for {symbol}")
                return False
            
            # Set up event handler for this specific bars object
            bars.updateEvent += lambda bars, hasNewBar, symbol=symbol: self._on_historical_update(bars, hasNewBar, symbol)
            
            print(f"✅ Successfully started real-time data for {symbol}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start real-time data for {symbol}: {e}")
            return False
    
    def _on_historical_update(self, bars, hasNewBar, symbol):
        """
        Internal handler for historical data updates
        Called when new bars are received from IBKR
        """
        if not hasNewBar:
            return
        
        # Get the latest bar (raw IBKR bar object)
        latest_bar = bars[-1]
        
        # Call the Bot's callback with raw bar data
        if self.on_new_bar:
            # Since onNewCandle is now async, schedule it as a task
            try:
                asyncio.create_task(self.on_new_bar(symbol, latest_bar))
            except Exception as e:
                print(f"❌ Error scheduling callback: {e}")
    
    def get_contract(self, symbol: str) -> Optional[Contract]:
        """Get the IBKR contract for a symbol"""
        return self.active_contracts.get(symbol)
    
    def get_active_symbols(self) -> list:
        """Get list of active symbols with contracts"""
        return list(self.active_contracts.keys())
    
    def start_ticker_subscription(self, symbol: str, generic_tick_list: str = '', 
                                 snapshot: bool = False, regulatory_snapshot: bool = False) -> bool:
        """
        Start real-time ticker/market data subscription for a symbol
        
        Args:
            symbol: Symbol to subscribe to
            generic_tick_list: Comma-separated tick types (e.g., '100,101,104')
            snapshot: Request snapshot instead of streaming
            regulatory_snapshot: Request regulatory snapshot
            
        Returns:
            True if successful, False otherwise
        """
        if symbol not in self.active_contracts:
            print(f"❌ No contract found for {symbol}")
            return False
        
        # Check if already subscribed using IBKR's native tracking
        if self.is_ticker_subscribed(symbol):
            print(f"⚠️ Already subscribed to ticker data for {symbol}")
            return True
        
        contract = self.active_contracts[symbol]
        if contract is None:
            print(f"❌ Contract for {symbol} is None")
            return False
        
        try:
            print(f"📡 Starting ticker subscription for {symbol}")
            
            # Request market data - IBKR handles tracking internally
            ticker = self.ib.reqMktData(
                contract=contract,
                genericTickList=generic_tick_list,
                snapshot=snapshot,
                regulatorySnapshot=regulatory_snapshot
            )
            
            if ticker is None:
                print(f"❌ Failed to create ticker for {symbol}")
                return False
            
            # Set up event handler for ticker updates
            event_handler = lambda ticker, symbol=symbol: self._on_ticker_update(ticker, symbol)
            ticker.updateEvent += event_handler
            
            # Store both the ticker object and event handler so we can disconnect properly
            self.ticker_objects[symbol] = ticker
            self.ticker_event_handlers[symbol] = event_handler
            
            print(f"✅ Successfully started ticker subscription for {symbol}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start ticker subscription for {symbol}: {e}")
            return False
    
    def stop_ticker_subscription(self, symbol: str) -> bool:
        """
        Stop real-time ticker/market data subscription for a symbol
        Uses IBKR's native ticker tracking to find and cancel subscriptions
        
        Args:
            symbol: Symbol to unsubscribe from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use our stored ticker object (exact same object we attached event handler to)
            if symbol not in self.ticker_objects:
                print(f"⚠️ No ticker object found for {symbol}")
                return True
            
            target_ticker = self.ticker_objects[symbol]
            print(f"🔄 Canceling ticker subscription for {symbol}")
            print(f"   Using stored ticker: {target_ticker.contract.symbol} (ConId: {target_ticker.contract.conId})")
            
            # First, disconnect the event handler from the exact same ticker object
            if symbol in self.ticker_event_handlers:
                event_handler = self.ticker_event_handlers[symbol]
                target_ticker.updateEvent -= event_handler
                del self.ticker_event_handlers[symbol]
                print(f"   Disconnected event handler for {symbol}")
            
            # Then cancel the market data stream
            result = self.ib.cancelMktData(target_ticker.contract)
            print(f"   cancelMktData result: {result}")
            
            # Clean up our tracking
            del self.ticker_objects[symbol]
            
            print(f"✅ Stopped ticker subscription for {symbol}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to stop ticker subscription for {symbol}: {e}")
            return False
    
    def _on_ticker_update(self, ticker: Ticker, symbol: str):
        """
        Internal handler for ticker updates
        Called when market data is received from IBKR
        """
        if not self.on_ticker_update:
            return
        
        print(f"🔄 Ticker update received for {symbol}")
        
        # Call the Bot's callback with native IBKR ticker object
        try:
            asyncio.create_task(self.on_ticker_update(symbol, ticker))
        except Exception as e:
            print(f"❌ Error scheduling ticker callback: {e}")
    
    def get_active_ticker_symbols(self) -> List[str]:
        """Get list of symbols with active ticker subscriptions (using IBKR's native tracking)"""
        return [ticker.contract.symbol for ticker in self.ib.tickers()]
    
    def is_ticker_subscribed(self, symbol: str) -> bool:
        """Check if symbol has active ticker subscription (using IBKR's native tracking)"""
        our_contract = self.active_contracts.get(symbol)
        if not our_contract:
            return False
        
        # Check: we have both the ticker object and event handler stored
        has_ticker_object = symbol in self.ticker_objects
        has_event_handler = symbol in self.ticker_event_handlers
        
        # Both should be true for a properly active subscription
        return has_ticker_object and has_event_handler
    
    def debug_ticker_subscriptions(self) -> List[Ticker]:
        """Debug method to check actual IBKR ticker subscriptions and our event handlers"""
        current_tickers = self.ib.tickers()
        print(f"🔍 IBKR has {len(current_tickers)} active ticker subscriptions:")
        
        for ticker in current_tickers:
            print(f"   - {ticker.contract.symbol} (ConId: {ticker.contract.conId})")
            print(f"     Last: {ticker.last}, Bid: {ticker.bid}, Ask: {ticker.ask}")
        
        print(f"🔍 We have {len(self.ticker_event_handlers)} active event handlers:")
        for symbol in self.ticker_event_handlers:
            print(f"   - {symbol}")
            
        print(f"🔍 We have {len(self.ticker_objects)} stored ticker objects:")
        for symbol in self.ticker_objects:
            print(f"   - {symbol}")
        
        return current_tickers
    
    def cleanup_orphaned_subscriptions(self):
        """Clean up any orphaned ticker subscriptions or event handlers"""
        print("🧹 Cleaning up orphaned subscriptions...")
        
        # Get symbols with IBKR subscriptions
        ibkr_symbols = set()
        for ticker in self.ib.tickers():
            ibkr_symbols.add(ticker.contract.symbol)
        
        # Get symbols with our event handlers
        handler_symbols = set(self.ticker_event_handlers.keys())
        
        # Find orphaned event handlers (we have handler but IBKR doesn't have subscription)
        orphaned_handlers = handler_symbols - ibkr_symbols
        for symbol in orphaned_handlers:
            print(f"🗑️ Removing orphaned event handler for {symbol}")
            if symbol in self.ticker_event_handlers:
                del self.ticker_event_handlers[symbol]
            if symbol in self.ticker_objects:
                del self.ticker_objects[symbol]
        
        # Find orphaned IBKR subscriptions (IBKR has subscription but we don't have handler)
        orphaned_subscriptions = ibkr_symbols - handler_symbols
        for symbol in orphaned_subscriptions:
            print(f"🗑️ Canceling orphaned IBKR subscription for {symbol}")
            self.stop_ticker_subscription(symbol)
        
        print(f"✅ Cleanup complete. Removed {len(orphaned_handlers)} handlers, {len(orphaned_subscriptions)} subscriptions") 