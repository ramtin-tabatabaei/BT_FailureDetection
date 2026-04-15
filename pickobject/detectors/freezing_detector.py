from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class FreezingDetector(FailureDetector):
    """Relays a freezing signal set by TemporalMonitorAgent (cheap sensor → VLM on image sequence)."""

    failure_type = "freezing"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
