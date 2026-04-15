from .action_timeout_detector import ActionTimeoutDetector
from .collision_detector import CollisionDetector
from .execution_mismatch_detector import ExecutionMismatchDetector
from .force_limit_exceeded_detector import ForceLimitExceededDetector
from .freezing_detector import FreezingDetector
from .grip_loss_detector import GripLossDetector
from .object_not_found_detector import ObjectNotFoundDetector
from .wrong_object_selection_detector import WrongObjectSelectionDetector
from .wrong_orientation_detector import WrongOrientationDetector
from .wrong_position_detector import WrongPositionDetector

DETECTOR_CLASSES = (
    ActionTimeoutDetector,
    CollisionDetector,
    ExecutionMismatchDetector,
    ForceLimitExceededDetector,
    FreezingDetector,
    GripLossDetector,
    ObjectNotFoundDetector,
    WrongObjectSelectionDetector,
    WrongOrientationDetector,
    WrongPositionDetector,
)

FAILURE_DETECTOR_CLASSES = {
    detector_class.failure_type: detector_class
    for detector_class in DETECTOR_CLASSES
}

__all__ = [
    "ActionTimeoutDetector",
    "CollisionDetector",
    "ExecutionMismatchDetector",
    "FAILURE_DETECTOR_CLASSES",
    "ForceLimitExceededDetector",
    "FreezingDetector",
    "GripLossDetector",
    "ObjectNotFoundDetector",
    "WrongObjectSelectionDetector",
    "WrongOrientationDetector",
    "WrongPositionDetector",
]
