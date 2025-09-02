"""
Fact Checkers Module

This module contains all fact checker implementations.
Each fact checker should be in its own subdirectory and registered with the registry.
"""

from .base import BaseFactChecker, FactCheckResult
from .registry import FactCheckerRegistry, register_fact_checker

# Import all fact checker implementations to register them
from .gpt5_v1 import GPT5FactCheckerV1

__all__ = [
    "BaseFactChecker",
    "FactCheckResult", 
    "FactCheckerRegistry",
    "register_fact_checker",
    "GPT5FactCheckerV1"
]