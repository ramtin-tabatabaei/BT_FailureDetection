from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import py_trees

from .config import DEFAULT_RETRY_BUDGET, FAILURE_CONFIG, MAX_TICKS, RECOVERY_CONFIG, TICK_PERIOD_SECONDS
from .failures import RUNTIME_FAILURE_TYPES
from .failure_manager import FailureDetectorManager
from .providers import (
    ChoiceProvider,
    ConditionProvider,
    NullActionMonitor,
    ScriptedChoiceProvider,
    ScriptedConditionProvider,
    TerminalChoiceProvider,
    TerminalConditionProvider,
    InteractiveActionMonitor,
)


def build_initial_world_state() -> Dict[str, Any]:
    return {
        "target_visible": None,
        "correct_object": None,
        "gripper_ready": None,
        "grasp_pose_valid": None,
        "object_in_gripper": None,
        "pick_succeeded": False,
        "last_failure": None,
        "last_failure_subtype": None,
        "recovery_action": None,
        "retry_counts": {},
        "current_bt_step": "Idle",
        "current_condition_name": None,
        "current_condition_phase": None,
        "current_condition_question": None,
        "last_valid_bt_step": "Idle",
        "last_recovery_options": [],
        "last_recovery_budget": None,
        "agent_inputs": {},
        "tick_count": 0,
        "tick_history": [],
    }


@dataclass
class PickObjectController:
    condition_provider: ConditionProvider
    choice_provider: ChoiceProvider
    failure_manager: FailureDetectorManager = field(default_factory=FailureDetectorManager)
    action_monitor: Any = field(default_factory=NullActionMonitor)
    state: Dict[str, Any] = field(default_factory=build_initial_world_state)
    root: Optional[py_trees.behaviour.Behaviour] = field(init=False, default=None)
    tree: Optional[py_trees.trees.BehaviourTree] = field(init=False, default=None)
    _current_tick_log: Optional[Dict[str, Any]] = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._current_tick_log = None
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        from .tree import make_pick_object_tree

        self.root = make_pick_object_tree(self)
        self.tree = py_trees.trees.BehaviourTree(self.root)

    def reset(self) -> None:
        self.state = build_initial_world_state()
        if hasattr(self.condition_provider, "clear"):
            self.condition_provider.clear()
        if hasattr(self.choice_provider, "clear"):
            self.choice_provider.clear()
        self.failure_manager.selector.reload()
        self._rebuild_tree()

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(self.state)

    def set_condition_response(self, check_name: str, value: bool) -> None:
        if not hasattr(self.condition_provider, "set_response"):
            raise RuntimeError("Active condition provider does not support scripted responses")
        self.condition_provider.set_response(check_name, value)

    def set_choice_response(self, prompt_key: str, value: str) -> None:
        if not hasattr(self.choice_provider, "set_choice"):
            raise RuntimeError("Active choice provider does not support scripted choices")
        self.choice_provider.set_choice(prompt_key, value)

    def set_agent_input(self, failure_type: str, detected: bool, **details: Any) -> None:
        self.state.setdefault("agent_inputs", {})[failure_type] = {"detected": detected, **details}

    def set_current_step(self, step_name: str) -> None:
        self.state["current_bt_step"] = step_name

    def set_current_condition(
        self,
        condition_name: Optional[str],
        phase: Optional[str],
        question: Optional[str] = None,
    ) -> None:
        self.state["current_condition_name"] = condition_name
        self.state["current_condition_phase"] = phase
        self.state["current_condition_question"] = question

    def check(self, check_name: str, description: str) -> bool:
        result = self.condition_provider.check(check_name, description, self.state)
        if self._current_tick_log is not None:
            self._current_tick_log["conditions_checked"].append({
                "condition_id": check_name,
                "result": result,
                "phase": self.state.get("current_condition_phase"),
                "bt_step": self.state.get("current_bt_step"),
            })
        return result

    def should_evaluate_hold_conditions(self) -> bool:
        return bool(getattr(self.condition_provider, "evaluate_hold_conditions", True))

    def choose(self, prompt_key: str, prompt: str, options: List[str], input_prompt: str) -> str:
        descriptions: Dict[str, str] = {}
        for option in options:
            descriptions[option] = (
                RECOVERY_CONFIG.get(option, {}).get("description")
                or FAILURE_CONFIG.get(option, {}).get("description", "")
            )
        self.state["pending_prompt_key"] = prompt_key
        try:
            return self.choice_provider.choose(prompt, options, descriptions, self.state, input_prompt)
        finally:
            self.state.pop("pending_prompt_key", None)

    def detect_failure(self, candidates: List[str], fallback: Optional[str] = None) -> Optional[str]:
        signal = self.failure_manager.detect(self.state, candidates)
        if signal is not None:
            self.state["last_failure"] = signal.failure_type
            self.state["last_failure_subtype"] = signal.subtype
            return signal.failure_type
        if fallback:
            self.state["last_failure"] = fallback
            self.state["last_failure_subtype"] = None
            return fallback
        return None

    def poll_runtime_failure(self, candidates: Optional[List[str]] = None) -> Optional[str]:
        runtime_candidates = candidates or list(RUNTIME_FAILURE_TYPES)
        signal = self.failure_manager.detect(self.state, runtime_candidates)
        if signal is None:
            return None
        self.state["last_failure"] = signal.failure_type
        self.state["last_failure_subtype"] = signal.subtype
        return signal.failure_type

    def mark_failure(self, failure_type: str, subtype: Optional[str] = None) -> str:
        self.state["last_failure"] = failure_type
        self.state["last_failure_subtype"] = subtype
        return failure_type

    def get_failure_recoveries(self, failure_type: str) -> List[str]:
        return list(FAILURE_CONFIG.get(failure_type, {}).get("recoveries", []))

    def get_failure_retry_budget(self, failure_type: str) -> int:
        return int(FAILURE_CONFIG.get(failure_type, {}).get("retry_budget", DEFAULT_RETRY_BUDGET))

    def get_recovery_context(self, failure_type: str) -> Dict[str, Any]:
        recoveries = self.get_failure_recoveries(failure_type)
        retry_count = int(self.state.setdefault("retry_counts", {}).get(failure_type, 0))
        retry_budget = self.get_failure_retry_budget(failure_type)
        self.state["last_recovery_options"] = recoveries
        self.state["last_recovery_budget"] = retry_budget
        return {
            "failure_type": failure_type,
            "recoveries": recoveries,
            "retry_count": retry_count,
            "retry_budget": retry_budget,
            "retries_remaining": max(retry_budget - retry_count, 0),
        }

    def clear_failure(self) -> None:
        self.state["last_failure"] = None
        self.state["last_failure_subtype"] = None

    def _resolve_recovery_resume_step(self, chosen_recovery: str) -> str:
        recovery_spec = RECOVERY_CONFIG.get(chosen_recovery, {})
        if isinstance(recovery_spec, dict):
            configured_step = recovery_spec.get("restart_step") or recovery_spec.get("resume_step")
            if configured_step:
                return str(configured_step)
        current_step = self.state.get("current_bt_step")
        if not current_step:
            raise RuntimeError("Cannot resume recovery: no current behaviour tree step is recorded.")
        return str(current_step)

    def _resume_tree_from_step(self, step_name: str) -> None:
        if self.root is None or self.tree is None:
            self._rebuild_tree()
        if self.root is None or not hasattr(self.root, "children"):
            raise RuntimeError("Cannot resume recovery: behaviour tree root is unavailable.")

        children = list(getattr(self.root, "children", []))
        target_child = next((child for child in children if child.name == step_name), None)
        if target_child is None:
            raise ValueError(f"Recovery resume step '{step_name}' is not part of the PickObject sequence.")

        self.root.current_child = target_child
        self.root.status = py_trees.common.Status.RUNNING
        target_index = children.index(target_child)
        for child in children[target_index:]:
            if child.status == py_trees.common.Status.RUNNING:
                child.stop(py_trees.common.Status.INVALID)
        self.state["current_bt_step"] = step_name

    def apply_recovery_choice(
        self,
        failure_type: str,
        chosen_recovery: str,
        reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        context = self.get_recovery_context(failure_type)
        recoveries = context["recoveries"]
        retry_count = context["retry_count"]
        retry_budget = context["retry_budget"]

        if chosen_recovery not in recoveries:
            raise ValueError(f"Recovery '{chosen_recovery}' is not configured for failure '{failure_type}'")
        if retry_count >= retry_budget:
            raise RuntimeError(
                f"Retry budget exhausted for failure '{failure_type}' ({retry_count}/{retry_budget})"
            )

        self.state.setdefault("retry_counts", {})[failure_type] = retry_count + 1
        self.state["recovery_action"] = chosen_recovery
        if reasoning and self.state.get("tick_history"):
            self.record_recovery_decision(failure_type, chosen_recovery, reasoning)

        resume_step = self._resolve_recovery_resume_step(chosen_recovery)
        self.clear_failure()
        self.state["current_condition_name"] = None
        self.state["current_condition_phase"] = None
        self.state["current_condition_question"] = None
        self._resume_tree_from_step(resume_step)
        return self.snapshot()

    def set_action_failure(self, failure_type: str, subtype: Optional[str] = None) -> py_trees.common.Status:
        self.state["last_failure"] = failure_type
        self.state["last_failure_subtype"] = subtype
        return py_trees.common.Status.FAILURE

    def record_recovery_decision(
        self, failure_type: str, chosen_recovery: str, reasoning: str
    ) -> None:
        """Log the agent's reasoning for a recovery decision.

        Call this after a tick fails and before resetting/retrying, so the
        reasoning is attached to the last tick entry in ``tick_history``.
        """
        entry = {
            "failure_type": failure_type,
            "chosen_recovery": chosen_recovery,
            "reasoning": reasoning,
        }
        history = self.state.get("tick_history", [])
        if history:
            history[-1]["recovery_decision"] = entry
        else:
            self.state.setdefault("tick_history", []).append({"recovery_decision": entry})

    def describe_tree(self) -> str:
        return py_trees.display.unicode_tree(self.root)

    def tick_once(self) -> Dict[str, Any]:
        if self.tree is None:
            self._rebuild_tree()

        tick_num = self.state.get("tick_count", 0)
        self._current_tick_log = {
            "tick": tick_num,
            "conditions_checked": [],
            "failure_detected": None,
            "tree_status": None,
            "bt_step": None,
            "recovery_decision": None,
        }
        self.state["tick_count"] = tick_num + 1

        self.tree.tick()

        self._current_tick_log["tree_status"] = str(self.root.status)
        self._current_tick_log["bt_step"] = self.state.get("current_bt_step")
        if self.state.get("last_failure"):
            self._current_tick_log["failure_detected"] = {
                "failure_type": self.state["last_failure"],
                "subtype": self.state.get("last_failure_subtype"),
            }

        self.state.setdefault("tick_history", []).append(self._current_tick_log)
        self._current_tick_log = None
        return self.snapshot()

    def run(self, max_ticks: int = MAX_TICKS, sleep_seconds: float = TICK_PERIOD_SECONDS) -> Dict[str, Any]:
        self._rebuild_tree()
        for tick_index in range(max_ticks):
            print(f"\n{'=' * 40}")
            print(f"  TICK {tick_index}")
            print(f"{'=' * 40}")
            # Keep manual mode aligned with tick_once so per-tick check caches expire.
            self.state["tick_count"] = tick_index + 1
            self.tree.tick()
            print(py_trees.display.unicode_tree(self.root, show_status=True))
            if self.state["pick_succeeded"]:
                print("\nPickObject finished successfully.")
                break
            if self.root.status == py_trees.common.Status.FAILURE:
                if not self._handle_failure_recovery():
                    break
                continue
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        else:
            print("\nMax ticks reached without success.")
        return self.snapshot()

    def _handle_failure_recovery(self) -> bool:
        failure_type = self.state.get("last_failure")
        if not failure_type:
            print("\n[Recovery] Tree failed without a configured failure type. Stopping run.")
            return False

        context = self.get_recovery_context(failure_type)
        recoveries = context["recoveries"]
        retry_count = context["retry_count"]
        retry_budget = context["retry_budget"]

        if not recoveries:
            print(f"\n[Recovery] No recovery options configured for '{failure_type}'. Stopping run.")
            return False
        if retry_count >= retry_budget:
            print(
                f"\n[Recovery] Retry budget exhausted for '{failure_type}' "
                f"({retry_count}/{retry_budget}). Stopping run."
            )
            return False

        prompt = (
            f"[Recovery] Failure '{failure_type}' detected at step "
            f"'{self.state.get('current_bt_step')}'. Choose a recovery "
            f"({retry_count + 1}/{retry_budget}):"
        )
        chosen_recovery = self.choose(
            f"recovery:{failure_type}:{retry_count + 1}",
            prompt,
            recoveries,
            "  Choose recovery by number or name: ",
        )
        self.apply_recovery_choice(
            failure_type,
            chosen_recovery,
            reasoning="Selected during interactive recovery prompt.",
        )
        print(f"[Recovery] Selected: {chosen_recovery}")
        print(f"[Recovery] Resuming PickObject from '{self.state.get('current_bt_step')}'.")
        return True

def create_scripted_controller() -> PickObjectController:
    return PickObjectController(
        condition_provider=ScriptedConditionProvider(),
        choice_provider=ScriptedChoiceProvider(),
        action_monitor=NullActionMonitor(),
    )


def create_interactive_controller() -> PickObjectController:
    return PickObjectController(
        condition_provider=TerminalConditionProvider(),
        choice_provider=TerminalChoiceProvider(),
        action_monitor=InteractiveActionMonitor(),
    )
