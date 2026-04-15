from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .agents import FAILURE_AGENT_CLASSES
from .agents.base import FailureAgent, FailureSignal
from .experiment import ExperimentFailureSelector


class FailureAgentManager:
    def __init__(self, selector: Optional[ExperimentFailureSelector] = None):
        self.selector = selector or ExperimentFailureSelector()
        self.agents: Dict[str, FailureAgent] = {
            failure_type: agent_class()
            for failure_type, agent_class in FAILURE_AGENT_CLASSES.items()
        }

    def enabled_failures(self) -> List[str]:
        return self.selector.get_enabled_failures()

    def detect(self, state: Dict[str, Any], candidates: Iterable[str]) -> Optional[FailureSignal]:
        for failure_type in candidates:
            if not self.selector.is_enabled(failure_type):
                continue
            agent = self.agents.get(failure_type)
            if agent is None:
                continue
            signal = agent.evaluate(state)
            if signal is not None and signal.detected:
                return signal
        return None
