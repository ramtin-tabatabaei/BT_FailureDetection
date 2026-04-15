from __future__ import annotations

from ..failures import RUNTIME_FAILURE_TYPES
from .base import TimedInterruptibleAction, failure_check


class LiftObject(TimedInterruptibleAction):
    runtime_failures = RUNTIME_FAILURE_TYPES
    preconditions = (
        failure_check(
            condition_id="ObjectInGripper",
            question="Before lifting, is the object currently held in the gripper?",
            failure_type="grip_loss",
        ),
    )
    hold_conditions = (
        failure_check(
            condition_id="ObjectInGripper",
            question="While lifting, is the object still held in the gripper?",
            failure_type="grip_loss",
        ),
    )
    postconditions = (
        failure_check(
            condition_id="FinalObjectInGripperCheck",
            question="After lifting, is the object still held securely in the gripper?",
            failure_type="grip_loss",
        ),
    )

    def __init__(self, name: str, controller):
        super().__init__(name, controller, "LiftObject", "Lifting object")

    def on_conditions_satisfied(self) -> None:
        self.controller.state["pick_succeeded"] = True
