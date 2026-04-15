from __future__ import annotations

from .base import InstantPlaceAction, failure_check


class ReleaseObject(InstantPlaceAction):
    """Open the gripper to release the object onto the target surface."""

    preconditions = (
        failure_check(
            condition_id="ObjectAtPlaceHeight",
            question="Before releasing, is the object resting at the correct height?",
            failure_type="collision_on_descent",
        ),
    )
    postconditions = (
        failure_check(
            condition_id="PlacementConfirmed",
            question="After releasing, is the object stably placed at the target location?",
            failure_type="placement_misaligned",
        ),
    )

    def on_success(self) -> None:
        self.controller.state["place_succeeded"] = True
