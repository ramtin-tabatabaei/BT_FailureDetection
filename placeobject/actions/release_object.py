from __future__ import annotations

from .base import TimedPlaceAction


class ReleaseObject(TimedPlaceAction):
    """Open the gripper to release the object onto the target surface."""

    action_text = "Releasing object"

    preconditions = (
        # failure_check(
        #     condition_id="ObjectAtPlaceHeight",
        #     question="Before releasing, is the object resting at the correct height?",
        #     failure_type="collision_on_descent",
        #     agent_name="PoseVerificationAgent",
        #     image_source="scene_camera",
        # ),
    )
    postconditions = (
        # failure_check(
        #     condition_id="PlacementConfirmed",
        #     question="After releasing, is the object stably placed at the target location?",
        #     failure_type="placement_misaligned",
        #     agent_name="ExecutionVerificationAgent",
        #     image_source="scene_camera",
        # ),
    )

    def on_success(self) -> None:
        self.controller.state["place_succeeded"] = True
