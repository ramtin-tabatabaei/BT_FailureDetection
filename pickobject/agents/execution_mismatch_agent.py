from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureAgent, FailureSignal


class ExecutionMismatchAgent(FailureAgent):
    failure_type = "execution_mismatch"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        details = self._input(state)
        subtype = details.get("subtype")
        return FailureSignal(self.failure_type, subtype=subtype, detected=True, details=details)
