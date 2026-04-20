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
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
        ),
        failure_check(
            condition_id="GripperReadyBeforeGrasp",
            question="Before moving to grasp, is the gripper open and ready?",
            failure_type="execution_mismatch",
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
        ),
    )
    hold_conditions = (
        failure_check(
            condition_id="GripperReadyBeforeGrasp",
            question="While moving to grasp, is the gripper still open and ready?",
            failure_type="execution_mismatch",
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
        ),
    )
    postconditions = ()

    def __init__(self, name: str, controller):
        super().__init__(name, controller, "MoveToGrasp", "Moving to grasp pose")

    def on_conditions_satisfied(self) -> None:
        pass
