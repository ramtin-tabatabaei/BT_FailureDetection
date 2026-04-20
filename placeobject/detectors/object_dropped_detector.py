from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class ObjectDroppedDetector(FailureDetector):
    """Relays an object_dropped signal set by InstantStateMonitorAgent (force sensor → VLM)."""

    failure_type = "object_dropped"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
