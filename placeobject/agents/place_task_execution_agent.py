from __future__ import annotations

from .base import PlaceObjectAgent


class PlaceTaskExecutionAgent(PlaceObjectAgent):
    """LLM — drives the PlaceObject BT tick loop and manages task progression."""

    name = "TaskExecutionAgent"
    modality = "LLM"
    description = (
        "Drives the PlaceObject BT tick loop via MCP place_* tools. "
        "Inspects state, advances the phase to done on success, and "
        "coordinates with RecoveryAgent on failure."
    )
    failure_types = ()
    condition_ids = ()

