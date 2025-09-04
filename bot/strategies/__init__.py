"""
Trading Strategies Module

Contains various trading strategies with their associated logic:
- Entry/exit strategy functions  
- Order cancellation strategies
- Strategy-specific configurations

Each strategy is organized in its own subdirectory as a Python module.
"""

# Version info
__version__ = "1.0.0"

# Available strategies
AVAILABLE_STRATEGIES = [
    "bollinger_bands",
    "moving_average",
]

def get_strategy_path(strategy_name: str, strategy_type: str = "strategy") -> str:
    """
    Get the file path for a strategy component
    
    Args:
        strategy_name: Name of the strategy (e.g., 'bollinger_bands')
        strategy_type: Type of strategy file ('strategy' or 'cancel_order_strategy')
    
    Returns:
        Path to the strategy file
    """
    if strategy_name not in AVAILABLE_STRATEGIES:
        raise ValueError(f"Strategy '{strategy_name}' not found. Available: {AVAILABLE_STRATEGIES}")
    
    if strategy_type == "strategy":
        return f"strategies/{strategy_name}/strategy.py"
    elif strategy_type == "cancel_order_strategy":
        return f"strategies/{strategy_name}/cancel_order_strategy.py"
    else:
        raise ValueError(f"Invalid strategy_type: {strategy_type}. Use 'strategy' or 'cancel_order_strategy'") 