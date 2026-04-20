from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class CollisionOnDescentDetector(FailureDetector):
    """Relays a collision_on_descent signal set by InstantStateMonitorAgent (force/torque sensor)."""

    failure_type = "collision_on_descent"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
