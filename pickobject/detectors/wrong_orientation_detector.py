from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class WrongOrientationDetector(FailureDetector):
    """Relays a wrong_orientation signal set by PoseVerificationAgent (cheap → VLM)."""

    failure_type = "wrong_orientation"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
