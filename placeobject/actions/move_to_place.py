from __future__ import annotations

from .base import InstantPlaceAction, failure_check


class MoveToPlace(InstantPlaceAction):
    """Move the arm (with the grasped object) to the target placement location."""

    preconditions = (
        failure_check(
            condition_id="ObjectSecuredInGripper",
            question="Before moving to place, is the object still secured in the gripper?",
            failure_type="object_dropped",
        ),
        failure_check(
            condition_id="PlaceLocationVisible",
            question="Before moving to place, is the placement location visible and reachable?",
            failure_type="placement_location_blocked",
        ),
    )
    postconditions = (
        failure_check(
            condition_id="AtPlaceLocation",
            question="After moving, is the robot correctly positioned above the placement location?",
            failure_type="placement_misaligned",
        ),
    )
