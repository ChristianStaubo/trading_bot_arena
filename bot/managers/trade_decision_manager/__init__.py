"""
Trade Decision Manager Package

Handles pure strategy execution and trade decisions for trading symbols.

Main Components:
- TradeDecisionManager: Core class for strategy execution
- Types: All type definitions (TradeSignal, CandleResult, etc.)
- Utils: Utility functions
"""

from .main import TradeDecisionManager
from .types import (
    TradeAction, ConfidenceLevel, StrategyFunction,
    TradeSignal, StrategySignalResult, CandleResult
)

__all__ = [
    'TradeDecisionManager',
    'TradeAction', 
    'ConfidenceLevel', 
    'StrategyFunction',
    'TradeSignal', 
    'StrategySignalResult', 
    'CandleResult',
] 