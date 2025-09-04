"""
MultiProcessManager - Bot Process Orchestration

Handles all multi-processing logic for running single or multiple trading bots.
Extracted from bot.py to improve modularity and separation of concerns.
"""

import sys
import os
import multiprocessing
import signal
import time
from typing import List, Dict

# Add parent directory to path for imports
sys.path.append('..')

from managers.logging_manager import LoggingManager


class MultiProcessManager:
    """
    Manages bot process orchestration and multiprocessing coordination
    
    Responsibilities:
    - Running single bot processes with proper signal handling
    - Coordinating multiple bot processes in parallel
    - System startup and configuration loading  
    - Graceful shutdown coordination
    - Process monitoring and error recovery
    """
    
    def __init__(self):
        """Initialize the MultiProcessManager"""
        # Set multiprocessing start method (important for cross-platform compatibility)
        multiprocessing.set_start_method('spawn', force=True)
        
        # Setup basic logging for manager operations
        self.logging_manager = LoggingManager()
        self.logger = self.logging_manager.get_combined_logger()
        
    def run_single_bot(self, bot_config: dict):
        """
        Run a single bot in its own process
        
        Args:
            bot_config: Dictionary containing bot configuration
        """
        try:
            print(f"🚀 Starting bot process: {bot_config['name']} (PID: {os.getpid()})")
            
            # Import Bot class here to avoid circular imports
            # Use absolute import since we're in managers/multi_process_manager/
            sys.path.append('../..')
            from bot import Bot
            
            # Create bot instance
            bot = Bot(
                name=bot_config['name'],
                symbol=bot_config['symbol'],
                exchange=bot_config['exchange'],
                asset_type=bot_config['asset_type'],
                strategy_name=bot_config['strategy_name'],
                strategy_path=bot_config['strategy_path'],
                cancel_strategy_path=bot_config.get('cancel_strategy_path'),
                default_quantity=bot_config.get('default_quantity', 2),
                max_concurrent_trades=bot_config.get('max_concurrent_trades', 1),
                timeframe=bot_config['timeframe'],
                client_id=bot_config['client_id']
            )
            
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                print(f"🛑 Bot {bot_config['name']} received shutdown signal")
                # The bot's cleanup will be handled by the finally block
                raise KeyboardInterrupt()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Run the bot
            bot.run()
            
        except KeyboardInterrupt:
            print(f"🛑 Bot {bot_config['name']} shutting down gracefully")
        except Exception as e:
            print(f"❌ Bot {bot_config['name']} crashed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"✅ Bot {bot_config['name']} process ended (PID: {os.getpid()})")

    def run_multiple_bots(self, bot_configs: List[dict]):
        """
        Run multiple bots in parallel using multiprocessing
            
        Args:
            bot_configs: List of bot configuration dictionaries
        """
        if not bot_configs:
            print("❌ No bot configurations provided")
            return
        
        print(f"🚀 Starting {len(bot_configs)} bots in parallel...")
        
        # Create processes for each bot
        processes = []
        
        try:
            for i, config in enumerate(bot_configs):
                # Ensure each bot has a unique client_id
                if 'client_id' not in config:
                    config['client_id'] = i + 1
                
                print(f"📋 Bot {i+1}: {config['name']} (Symbol: {config['symbol']}, Client ID: {config['client_id']})")
                
                # Create process
                process = multiprocessing.Process(
                    target=self.run_single_bot,
                    args=(config,),
                    name=f"Bot-{config['name']}"
                )
                
                processes.append(process)
            
            # Start all processes
            print(f"\n🔄 Starting {len(processes)} bot processes...")
            for process in processes:
                process.start()
                print(f"✅ Started {process.name} (PID: {process.pid})")
                time.sleep(2)  # Small delay between starts to avoid IBKR connection issues
            
            print(f"\n🎯 All {len(processes)} bots are now running!")
            print("📊 Monitor individual bot logs in bot/logs/")
            print("🛑 Press Ctrl+C to stop all bots")
            
            # Wait for all processes to complete
            try:
                for process in processes:
                    process.join()
            except KeyboardInterrupt:
                print("\n🛑 Shutdown signal received - stopping all bots...")
                
                # Terminate all processes gracefully
                for process in processes:
                    if process.is_alive():
                        print(f"🛑 Stopping {process.name}...")
                        process.terminate()
                
                # Wait for graceful shutdown
                print("⏱️ Waiting for bots to shut down gracefully...")
                for process in processes:
                    process.join(timeout=10)
                    if process.is_alive():
                        print(f"⚠️ Force killing {process.name}")
                        process.kill()
                        process.join()
                
                print("✅ All bots stopped")
                
        except Exception as e:
            print(f"❌ Error in multi-bot manager: {e}")
            # Emergency cleanup
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
            raise

    def run_system(self):
        """
        Main system entry point - loads configurations and starts the bot system
        """
        try:
            # Display logging status
            print(f"🔍 Logtail integration: {self.logging_manager.get_logtail_status()}")
            
            # Import bot configurations
            from lib.config.multi_bot_config import get_development_bot_configs
            
            # Get bot configurations (using development configs for now)
            bot_configs = get_development_bot_configs()
            
            print(f"🚀 Starting trading bot system...")
            print(f"📊 Configured {len(bot_configs)} bots")
            
            for i, config in enumerate(bot_configs, 1):
                print(f"  {i}. {config['name']} ({config['symbol']}) - {config['strategy_name']}")
            
            # Run multiple bots
            self.run_multiple_bots(bot_configs)
            
        except Exception as e:
            print(f"❌ System startup failed: {e}")
            import traceback
            traceback.print_exc()
            raise