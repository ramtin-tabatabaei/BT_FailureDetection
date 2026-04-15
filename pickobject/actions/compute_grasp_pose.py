from __future__ import annotations

from .base import InstantAction, failure_check


class ComputeGraspPose(InstantAction):
    preconditions = (
        failure_check(
            condition_id="TargetVisible",
            question="Can the robot currently see the target object?",
            failure_type="object_not_found",
        ),
    )

    def perform_action(self) -> None:
        print("[Action] Computing grasp pose")

    def on_conditions_satisfied(self) -> None:
        pass
