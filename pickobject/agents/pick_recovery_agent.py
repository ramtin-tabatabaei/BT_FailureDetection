from __future__ import annotations

from .base import PickObjectAgent


class PickRecoveryAgent(PickObjectAgent):
    name = "RecoveryAgent"
    modality = "LLM"
    description = "Chooses and applies a recovery strategy after a BT failure is detected."
    failure_types = ()
    condition_ids = ()

