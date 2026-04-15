from __future__ import annotations

from .base import InstantPlaceAction, failure_check


class LowerObject(InstantPlaceAction):
    """Lower the object from the approach height down onto the target surface."""

    preconditions = (
        failure_check(
            condition_id="AtPlaceLocation",
            question="Before lowering, is the robot at the correct placement location?",
            failure_type="placement_misaligned",
        ),
    )
    postconditions = (
        failure_check(
            condition_id="ObjectAtPlaceHeight",
            question="After lowering, is the object at the correct height on the target surface?",
            failure_type="collision_on_descent",
        ),
    )
