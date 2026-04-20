from __future__ import annotations

from typing import Any, Dict, Optional

from .base import FailureDetector, FailureSignal


class PlacementLocationBlockedDetector(FailureDetector):
    """Relays a placement_location_blocked signal set by ScenePerceptionAgent (VLM)."""

    failure_type = "placement_location_blocked"

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
