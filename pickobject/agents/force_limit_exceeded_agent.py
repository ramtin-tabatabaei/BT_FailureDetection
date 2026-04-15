from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureAgent, FailureSignal


class ForceLimitExceededAgent(FailureAgent):
    failure_type = "force_limit_exceeded"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
