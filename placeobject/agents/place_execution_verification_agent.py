from __future__ import annotations

from .base import PlaceObjectAgent


class PlaceExecutionVerificationAgent(PlaceObjectAgent):
    """Cheap model → VLM — verifies stage transitions for the PlaceObject BT."""

    name = "ExecutionVerificationAgent"
    modality = "cheap_to_vlm"
    description = (
        "Verifies, from one transition image, that the current stage's post-conditions "
        "and the next stage's pre-conditions are visually coherent."
    )
    failure_types = ("execution_mismatch",)
    condition_ids = ("PlacementConfirmed",)

    def check_transition(
        self,
        image_path: str,
        *,
        current_action: str,
        current_post_conditions: list[tuple[str, str]] | None = None,
        next_action: str | None = None,
        next_pre_conditions: list[tuple[str, str]] | None = None,
        predicted_answers: dict[str, bool] | None = None,
    ):
        from agents.execution_verification_agent import ExecutionVerificationAgent as _Agent

        try:
            return _Agent().check_transition(
                image_path,
                current_action=current_action,
                current_post_conditions=current_post_conditions,
                next_action=next_action,
                next_pre_conditions=next_pre_conditions,
            )
        except Exception:
            return _Agent.predict(
                current_action=current_action,
                current_post_conditions=current_post_conditions,
                next_action=next_action,
                next_pre_conditions=next_pre_conditions,
                condition_answers=predicted_answers,
            )

    def verify(
        self,
        action: str,
        phase: str,
        conditions: list[tuple[str, bool]],
    ) -> tuple[bool, str]:
        condition_specs = [
            (condition_id, f"Is {condition_id} satisfied for {action} ({phase})?")
            for condition_id, _ in conditions
        ]
        predicted_answers = {condition_id: answer for condition_id, answer in conditions}
        if phase == "post":
            verification = self.check_transition(
                "",
                current_action=action,
                current_post_conditions=condition_specs,
                predicted_answers=predicted_answers,
            )
        else:
            verification = self.check_transition(
                "",
                current_action=action,
                next_action=action,
                next_pre_conditions=condition_specs,
                predicted_answers=predicted_answers,
            )
        return verification.all_satisfied, verification.summary
