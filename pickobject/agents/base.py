from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class FailureSignal:
    failure_type: str
    subtype: Optional[str] = None
    detected: bool = False
    details: Dict[str, Any] | None = None


class FailureAgent:
    failure_type: str = ""

    def evaluate(self, state: Dict[str, Any]) -> Optional[FailureSignal]:
        raise NotImplementedError

    def _input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        agent_inputs = state.setdefault("agent_inputs", {})
        return agent_inputs.setdefault(self.failure_type, {})

    def _is_triggered(self, state: Dict[str, Any]) -> bool:
        return bool(self._input(state).get("detected", False))
