from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class ExecutionMismatchDetector(FailureDetector):
    """Relays an execution_mismatch signal set by ExecutionVerificationAgent (cheap → VLM)."""

    failure_type = "execution_mismatch"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
