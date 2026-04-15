from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .detectors import FAILURE_DETECTOR_CLASSES
from .detectors.base import FailureDetector, FailureSignal
from .experiment import ExperimentFailureSelector


class FailureDetectorManager:
    """Manages a registry of FailureDetector instances.

    Iterates through the enabled detectors on each call to ``detect`` and
    returns the first signal that is triggered.  Detectors are rule-based
    relay components — they do not reason; they check a flag set by an
    external agent (VLM, sensor monitor, or MCP tool call) and forward
    the signal to the BT.
    """

    def __init__(self, selector: Optional[ExperimentFailureSelector] = None):
        self.selector = selector or ExperimentFailureSelector()
        self.detectors: Dict[str, FailureDetector] = {
            failure_type: detector_class()
            for failure_type, detector_class in FAILURE_DETECTOR_CLASSES.items()
        }

    def enabled_failures(self) -> List[str]:
        return self.selector.get_enabled_failures()

    def detect(self, state: Dict[str, Any], candidates: Iterable[str]) -> Optional[FailureSignal]:
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
