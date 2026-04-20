from __future__ import annotations

from typing import Set

from .failures import FAILURE_CONFIG


class PlaceExperimentFailureSelector:
    """Controls which failure types are active during a PlaceObject experiment.

    Mirrors :class:`pickobject.experiment.ExperimentFailureSelector`.
    All failures are enabled by default; individual ones can be toggled
    for specific experiment configurations.
    """

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.enabled_failures: Set[str] = set(FAILURE_CONFIG.keys())

    def is_enabled(self, failure_type: str) -> bool:
        return failure_type in self.enabled_failures

    def get_enabled_failures(self) -> list[str]:
        return [name for name in FAILURE_CONFIG.keys() if name in self.enabled_failures]
