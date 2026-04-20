from .action_timeout_detector import ActionTimeoutDetector
from .collision_on_descent_detector import CollisionOnDescentDetector
from .execution_mismatch_detector import ExecutionMismatchDetector
from .freezing_detector import FreezingDetector
from .object_dropped_detector import ObjectDroppedDetector
from .placement_location_blocked_detector import PlacementLocationBlockedDetector
from .placement_misaligned_detector import PlacementMisalignedDetector

DETECTOR_CLASSES = (
    ActionTimeoutDetector,
    CollisionOnDescentDetector,
    ExecutionMismatchDetector,
    FreezingDetector,
    ObjectDroppedDetector,
    PlacementLocationBlockedDetector,
    PlacementMisalignedDetector,
)

FAILURE_DETECTOR_CLASSES: dict[str, type] = {
    detector_class.failure_type: detector_class
    for detector_class in DETECTOR_CLASSES
}

__all__ = [
    "ActionTimeoutDetector",
    "CollisionOnDescentDetector",
    "DETECTOR_CLASSES",
    "ExecutionMismatchDetector",
    "FAILURE_DETECTOR_CLASSES",
    "FreezingDetector",
    "ObjectDroppedDetector",
    "PlacementLocationBlockedDetector",
    "PlacementMisalignedDetector",
]
