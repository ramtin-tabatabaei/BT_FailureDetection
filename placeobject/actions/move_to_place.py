from __future__ import annotations

from .base import TimedPlaceAction, failure_check


class MoveToPlace(TimedPlaceAction):
    """Move the arm (with the grasped object) to the target placement location."""

    action_text = "Moving to place location"

    preconditions = (
        # failure_check(
        #     condition_id="ObjectSecuredInGripper",
        #     question="Before moving to place, is the object still secured in the gripper?",
        #     failure_type="object_dropped",
        #     agent_name="GraspVerificationAgent",
        #     image_source="wrist_camera",
        # ),
        failure_check(
            condition_id="PlaceLocationVisible",
            question="Before moving to place, is the placement location visible and reachable?",
            failure_type="placement_location_blocked",
            agent_name="ScenePerceptionAgent",
            image_source="scene_camera",
        ),
    # )
    # postconditions = (
    #     failure_check(
    #         condition_id="AtPlaceLocation",
    #         question="After moving, is the robot correctly positioned above the placement location?",
    #         failure_type="placement_misaligned",
    #         agent_name="PoseVerificationAgent",
    #         image_source="scene_camera",
    #     ),
    )
