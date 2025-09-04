"""
Multi-Process Manager

Handles bot process orchestration, multiprocessing coordination, and system lifecycle management.
Extracted from bot.py to improve separation of concerns and maintainability.

This manager is responsible for:
- Running single bot processes
- Coordinating multiple bot processes  
- System startup and configuration loading
- Graceful shutdown handling
- Process monitoring and error recovery
"""

# Make MultiProcessManager available at package level
from .main import MultiProcessManager

__all__ = ['MultiProcessManager']