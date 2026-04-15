from __future__ import annotations

from ..failures import RUNTIME_FAILURE_TYPES
from .base import TimedInterruptibleAction, failure_check


class MoveToGrasp(TimedInterruptibleAction):
    runtime_failures = RUNTIME_FAILURE_TYPES
    preconditions = (
        failure_check(
            condition_id="PreGraspPoseConfirmed",
            question="Before moving to grasp, is the robot correctly at the pre-grasp pose?",
            failure_type="execution_mismatch",
        ),
        failure_check(
            condition_id="GripperReadyBeforeGrasp",
            question="Before moving to grasp, is the gripper open and ready?",
            failure_type="execution_mismatch",
        ),
    )
    hold_conditions = ()
    postconditions = ()

    def __init__(self, name: str, controller):
        super().__init__(name, controller, "MoveToGrasp", "Moving to grasp pose")

    def on_conditions_satisfied(self) -> None:
        pass
