from __future__ import annotations

from typing import Any

from .base import RecoveryDecision


class RecoveryAgent:
    """LLM-style recovery agent with a small policy for demo predictions."""

    _PREFERRED_ORDER = {
        "object_not_found": ("rescan_scene", "search_workspace", "verify_scene_setup_with_operator"),
        "wrong_object_selection": ("candidate_elimination_and_reselection", "ask_user"),
        "wrong_position": ("reestimate_object_pose", "regrasp", "ask_user"),
        "wrong_orientation": ("reestimate_object_pose", "regrasp", "ask_user"),
        "execution_mismatch": (
            "re_evaluate_current_state",
            "insert_missing_step_into_plan",
            "replace_with_valid_action",
            "reorder_actions",
        ),
        "freezing": ("cancel_current_action", "reset_controller_or_motion_planner", "return_to_last_known_safe_state"),
        "grip_loss": ("stop_motion_immediately", "re_approach_and_regrasp", "search_for_dropped_object"),
        "collision": ("stop_immediately", "retract_to_safe_pose", "replan_motion_path"),
        "force_limit_exceeded": ("stop_motion", "retract_to_safe_pose", "re_align_end_effector_before_retry"),
        "action_timeout": ("abort_current_action", "retreat_to_previous_stable_state", "retry_with_adjusted_parameters"),
    }

    def get_context(self, controller: Any, failure_type: str) -> dict[str, Any]:
        return controller.get_recovery_context(failure_type)

    def choose(self, controller: Any, failure_type: str) -> RecoveryDecision:
        context = self.get_context(controller, failure_type)
        available = list(context.get("recoveries", []))
        if not available:
            raise ValueError(f"No recoveries configured for failure '{failure_type}'")

        preferred = self._PREFERRED_ORDER.get(failure_type, ())
        chosen = next((item for item in preferred if item in available), available[0])
        reasoning = self._build_reasoning(failure_type, chosen, context)
        return RecoveryDecision(chosen_recovery=chosen, reasoning=reasoning)

    def apply(self, controller: Any, failure_type: str, decision: RecoveryDecision) -> dict[str, Any]:
        return controller.apply_recovery_choice(
            failure_type,
            decision.chosen_recovery,
            decision.reasoning,
        )

    def get_history(self, controller: Any) -> list[dict[str, Any]]:
        return [
            entry["recovery_decision"]
            for entry in controller.state.get("tick_history", [])
            if entry.get("recovery_decision")
        ]

    def _build_reasoning(self, failure_type: str, chosen: str, context: dict[str, Any]) -> str:
        retry_count = context.get("retry_count", 0)
        retries_remaining = context.get("retries_remaining", 0)
        return (
            f"The active failure is {failure_type}. "
            f"{chosen} is a configured recovery for this failure and is the least disruptive "
            f"available option at retry {retry_count + 1}. "
            f"Retries remaining after this choice: {retries_remaining - 1 if retries_remaining else 0}."
        )
