"""
Trading Bot Package

Main trading bot package containing the core Bot class and all manager components.
This package provides a complete trading bot system with multiprocessing support,
strategy management, order handling, and comprehensive logging.

Main Components:
- Bot: Core trading bot class
- MultiProcessManager: Process orchestration and coordination
- Various specialized managers for different aspects of trading
"""

# Import the main Bot class for easy access
from .bot import Bot

# Import the MultiProcessManager for easy access
from .managers.multi_process_manager import MultiProcessManager

# Define what gets exported when using "from bot import *"
__all__ = [
    'Bot',
    'MultiProcessManager'
]

# Package metadata
__version__ = '2.0.0'
__author__ = 'Trading Bot Team'
__description__ = 'Multi-process trading bot with modular architecture'