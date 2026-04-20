from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class PlacementMisalignedDetector(FailureDetector):
    """Relays a placement_misaligned signal set by PoseVerificationAgent (cheap model → VLM)."""

    failure_type = "placement_misaligned"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
