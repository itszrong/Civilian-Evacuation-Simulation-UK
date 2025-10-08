"""
Evaluation Framework for London Evacuation Planning Tool

Provides evaluation capabilities against golden standards derived from
UK Mass Evacuation Framework and historical exercises.
"""

from .evaluator import FrameworkEvaluator

__version__ = "1.0.0"
__all__ = ["FrameworkEvaluator"]
