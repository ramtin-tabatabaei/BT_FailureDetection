from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class CollisionDetector(FailureDetector):
    """Relays a collision signal set by InstantStateMonitorAgent (force/torque sensor → VLM single frame)."""

    failure_type = "collision"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
