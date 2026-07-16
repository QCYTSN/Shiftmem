"""Deterministic control plane for the v2 hierarchical strategy agent.

The controller computes every daily order from public information and the
current validated strategy vector. The scheduler decides when the low-frequency
LLM strategy review may run. Neither component may call a provider or read
hidden environment truth.
"""

from .controller import DeterministicController, StrategyParameters

__all__ = ["DeterministicController", "StrategyParameters"]
