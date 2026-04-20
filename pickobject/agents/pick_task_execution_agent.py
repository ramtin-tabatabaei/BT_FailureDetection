from __future__ import annotations

from .base import PickObjectAgent


class PickTaskExecutionAgent(PickObjectAgent):
    name = "TaskExecutionAgent"
    modality = "LLM"
    description = "Drives the BT tick loop, inspects state, and manages task progression."
    failure_types = ()
    condition_ids = ()

