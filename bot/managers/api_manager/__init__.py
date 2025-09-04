"""
API Manager Package

Handles all API communication between the bot and the backend service.
Centralizes HTTP requests, error handling, and response processing.

Structure:
- main.py: Core ApiManager class and functionality
"""

from .main import ApiManager

__all__ = ['ApiManager']