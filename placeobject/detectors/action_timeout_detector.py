from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class ActionTimeoutDetector(FailureDetector):
    """Relays an action_timeout signal set by TemporalMonitorAgent (timer → image sequence)."""

    failure_type = "action_timeout"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
