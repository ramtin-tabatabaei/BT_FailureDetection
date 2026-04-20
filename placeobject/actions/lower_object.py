from __future__ import annotations

from .base import TimedPlaceAction, failure_check


class LowerObject(TimedPlaceAction):
    """Lower the object from the approach height down onto the target surface."""

    action_text = "Lowering object onto surface"

    preconditions = (
        # failure_check(
        #     condition_id="AtPlaceLocation",
        #     question="Before lowering, is the robot at the correct placement location?",
        #     failure_type="placement_misaligned",
        #     agent_name="PoseVerificationAgent",
        #     image_source="scene_camera",
        # ),
    )
    postconditions = (
        # failure_check(
        #     condition_id="ObjectAtPlaceHeight",
        #     question="After lowering, is the object at the correct height on the target surface?",
        #     failure_type="collision_on_descent",
        #     agent_name="PoseVerificationAgent",
        #     image_source="scene_camera",
        # ),
    )
