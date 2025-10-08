"""
Orchestration services module.
Contains high-level orchestration and coordination services.
"""

from .multi_city_orchestrator import EvacuationOrchestrator

# The monolithic 1,722-line orchestrator has been refactored into focused services.
# This import now uses the slim 147-line refactored version.
# The old version is preserved as multi_city_orchestrator_old.py for reference.
