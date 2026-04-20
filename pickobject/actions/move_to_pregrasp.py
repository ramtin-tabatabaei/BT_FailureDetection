from __future__ import annotations

from ..failures import RUNTIME_FAILURE_TYPES
from .base import TimedInterruptibleAction, failure_check


class MoveToPreGrasp(TimedInterruptibleAction):
    runtime_failures = RUNTIME_FAILURE_TYPES
    preconditions = (
        failure_check(
            condition_id="TargetVisible",
            question="Can the robot currently see the target object?",
            failure_type="object_not_found",
            agent_name="ScenePerceptionAgent",
            detector_name="ObjectNotFoundDetector",
        ),
        failure_check(
            condition_id="GripperReadyBeforeGrasp",
            question="Is the gripper open and ready to grasp?",
            failure_type="execution_mismatch",
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
        ),
    )
    hold_conditions = (
        failure_check(
            condition_id="GripperReadyBeforeGrasp",
            question="While moving to pre-grasp, is the gripper still open and ready?",
            failure_type="execution_mismatch",
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
        ),
    )
    postconditions = (
        failure_check(
            condition_id="GripperReadyBeforeGrasp",
            question="After moving to pre-grasp, is the gripper still open and ready?",
            failure_type="execution_mismatch",
            agent_name="ExecutionVerificationAgent",
            detector_name="ExecutionMismatchDetector",
        ),
    )

    def __init__(self, name: str, controller):
        super().__init__(name, controller, "MoveToPreGrasp", "Moving to pre-grasp pose")

    def on_conditions_satisfied(self) -> None:
        pass
