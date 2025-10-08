"""
Simple Metrics Builder

A straightforward pandas-based system for calculating metrics on simulation data.
No SQL complexity - just clean Python operations on DataFrames.
"""

from .builder import MetricsBuilder
from .operations import MetricsOperations

__version__ = "0.1.0"
__all__ = ["MetricsBuilder", "MetricsOperations"]
