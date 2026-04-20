from __future__ import annotations

from .base import PlaceObjectAgent


class PlaceRecoveryAgent(PlaceObjectAgent):
    """LLM — chooses and applies a recovery strategy after a PlaceObject failure."""

    name = "RecoveryAgent"
    modality = "LLM"
    description = (
        "Chooses and applies a recovery strategy after a PlaceObject BT "
        "failure. Reasons about the failure type, available recoveries, "
        "and retry budget before committing to an action."
    )
    failure_types = ()
    condition_ids = ()

