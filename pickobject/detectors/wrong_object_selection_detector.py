from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class WrongObjectSelectionDetector(FailureDetector):
    """Relays a wrong_object_selection signal set by GraspVerificationAgent (VLM)."""

    failure_type = "wrong_object_selection"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
