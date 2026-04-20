from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .detectors import FAILURE_DETECTOR_CLASSES
from .detectors.base import FailureDetector, FailureSignal
from .experiment import PlaceExperimentFailureSelector


class PlaceFailureDetectorManager:
    """Manages a registry of PlaceObject FailureDetector instances.

    Mirrors :class:`pickobject.failure_manager.FailureDetectorManager`.

    Iterates through enabled detectors on each call to ``detect`` and returns
    the first triggered signal.  Detectors are rule-based relay components —
    they check a flag set by an external agent and forward the signal to the BT.
    """

    def __init__(self, selector: Optional[PlaceExperimentFailureSelector] = None) -> None:
        self.selector = selector or PlaceExperimentFailureSelector()
        self.detectors: Dict[str, FailureDetector] = {
            failure_type: detector_class()
            for failure_type, detector_class in FAILURE_DETECTOR_CLASSES.items()
        }

    def enabled_failures(self) -> List[str]:
        return self.selector.get_enabled_failures()

    def detect(
        self, state: Dict[str, Any], candidates: Iterable[str]
    ) -> Optional[FailureSignal]:
        for failure_type in candidates:
            if not self.selector.is_enabled(failure_type):
                continue
            detector = self.detectors.get(failure_type)
            if detector is None:
                continue
            signal = detector.evaluate(state)
            if signal is not None and signal.detected:
                return signal
        return None
