from __future__ import annotations

from ..failures import RUNTIME_FAILURE_TYPES
from .base import TimedInterruptibleAction, failure_check


class CloseGripper(TimedInterruptibleAction):
    runtime_failures = RUNTIME_FAILURE_TYPES
    preconditions = (
        failure_check(
            condition_id="GripperReady",
            question="Before closing the gripper, is the gripper open and ready?",
            failure_type="execution_mismatch",
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
            image_source="gripper_camera",
        ),
        failure_check(
            condition_id="CorrectObjectSelected",
            question="Before closing the gripper, is the selected object the correct target?",
            failure_type="wrong_object_selection",
            agent_name="GraspVerificationAgent",
            detector_name="WrongObjectSelectionDetector",
            image_source="wrist_camera",
        ),
        failure_check(
            condition_id="GraspPositionAligned",
            question="Before closing the gripper, is the gripper position correctly aligned with the target?",
            failure_type="wrong_position",
            agent_name="PoseVerificationAgent",
            detector_name="WrongPositionDetector",
            image_source="wrist_camera",
        ),
        failure_check(
            condition_id="GraspOrientationAligned",
            question="Before closing the gripper, is the gripper orientation correct for grasping?",
            failure_type="wrong_orientation",
            agent_name="PoseVerificationAgent",
            detector_name="WrongOrientationDetector",
            image_source="wrist_camera",
        ),
    )
    hold_conditions = ()
    postconditions = (
        failure_check(
            condition_id="ObjectInGripper",
            question="After closing the gripper, is the object currently held in the gripper?",
            failure_type="grip_loss",
            agent_name="InstantStateMonitorAgent",
            detector_name="GripLossDetector",
        ),
    )

    def __init__(self, name: str, controller):
        super().__init__(name, controller, "CloseGripper", "Closing gripper")

    def on_conditions_satisfied(self) -> None:
        pass
