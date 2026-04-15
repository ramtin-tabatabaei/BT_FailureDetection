from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import py_trees

from .failures import FAILURE_CONFIG

# Re-use the same provider classes from pickobject — they are generic and not
# pickobject-specific.
from pickobject.providers import ScriptedConditionProvider


def build_initial_world_state() -> Dict[str, Any]:
    return {
        "at_place_location": None,
        "object_at_place_height": None,
        "place_succeeded": False,
        "last_failure": None,
        "last_failure_subtype": None,
        "recovery_action": None,
        "retry_counts": {},
        "current_bt_step": "Idle",
        "current_condition_name": None,
        "current_condition_phase": None,
        "current_condition_question": None,
        "agent_inputs": {},
        "tick_count": 0,
        "tick_history": [],
    }


@dataclass
class PlaceObjectController:
    """BT controller for the PlaceObject task.

    Mirrors the interface of :class:`pickobject.controller.PickObjectController`
    so that MCP tool implementations can be uniform across both agents.
    """

    condition_provider: Any
    state: Dict[str, Any] = field(default_factory=build_initial_world_state)
    root: Optional[py_trees.behaviour.Behaviour] = field(init=False, default=None)
    tree: Optional[py_trees.trees.BehaviourTree] = field(init=False, default=None)
    _current_tick_log: Optional[Dict[str, Any]] = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._current_tick_log = None
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        from .tree import make_place_object_tree
        self.root = make_place_object_tree(self)
        self.tree = py_trees.trees.BehaviourTree(self.root)

    # ── State management ──────────────────────────────────────────────────────

    def reset(self) -> None:
        self.state = build_initial_world_state()
        if hasattr(self.condition_provider, "clear"):
            self.condition_provider.clear()
        self._rebuild_tree()

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(self.state)

    def set_condition_response(self, check_name: str, value: bool) -> None:
        if not hasattr(self.condition_provider, "set_response"):
            raise RuntimeError("Active condition provider does not support scripted responses")
        self.condition_provider.set_response(check_name, value)

    def set_agent_input(self, failure_type: str, detected: bool, **details: Any) -> None:
        """Inject a runtime failure signal (mirrors PickObjectController API)."""
        self.state.setdefault("agent_inputs", {})[failure_type] = {
            "detected": detected,
            **details,
        }
        if detected:
            self.state["last_failure"] = failure_type
            self.state["last_failure_subtype"] = details.get("subtype")

    # ── BT step tracking ──────────────────────────────────────────────────────

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

    # ── Failure handling ──────────────────────────────────────────────────────

    def detect_failure(
        self, candidates: List[str], fallback: Optional[str] = None
    ) -> Optional[str]:
        """Set the first candidate as the active failure (no agent-based detection)."""
        failure_type = candidates[0] if candidates else fallback
        if failure_type:
            self.state["last_failure"] = failure_type
            self.state["last_failure_subtype"] = None
        return failure_type

    def mark_failure(self, failure_type: str, subtype: Optional[str] = None) -> str:
        self.state["last_failure"] = failure_type
        self.state["last_failure_subtype"] = subtype
        return failure_type

    def clear_failure(self) -> None:
        self.state["last_failure"] = None
        self.state["last_failure_subtype"] = None

    def get_failure_recoveries(self, failure_type: str) -> List[str]:
        return list(FAILURE_CONFIG.get(failure_type, {}).get("recoveries", []))

    def get_failure_retry_budget(self, failure_type: str) -> int:
        return int(FAILURE_CONFIG.get(failure_type, {}).get("retry_budget", 1))

    def get_recovery_context(self, failure_type: str) -> Dict[str, Any]:
        recoveries = self.get_failure_recoveries(failure_type)
        retry_count = int(self.state.setdefault("retry_counts", {}).get(failure_type, 0))
        retry_budget = self.get_failure_retry_budget(failure_type)
        return {
            "failure_type": failure_type,
            "recoveries": recoveries,
            "retry_count": retry_count,
            "retry_budget": retry_budget,
            "retries_remaining": max(retry_budget - retry_count, 0),
        }

    def apply_recovery_choice(
        self,
        failure_type: str,
        chosen_recovery: str,
        reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply a recovery decision and rebuild the BT from the start of the sequence.

        For PlaceObject, recovery always restarts the full sequence (simpler than
        per-step resumption).  The agent's reasoning is logged to tick history.
        """
        context = self.get_recovery_context(failure_type)
        recoveries = context["recoveries"]
        retry_count = context["retry_count"]
        retry_budget = context["retry_budget"]

        if chosen_recovery not in recoveries:
            raise ValueError(
                f"Recovery '{chosen_recovery}' is not configured for failure '{failure_type}'"
            )
        if retry_count >= retry_budget:
            raise RuntimeError(
                f"Retry budget exhausted for failure '{failure_type}' "
                f"({retry_count}/{retry_budget})"
            )

        self.state.setdefault("retry_counts", {})[failure_type] = retry_count + 1
        self.state["recovery_action"] = chosen_recovery

        if reasoning and self.state.get("tick_history"):
            self.record_recovery_decision(failure_type, chosen_recovery, reasoning)

        self.clear_failure()
        self.state["current_condition_name"] = None
        self.state["current_condition_phase"] = None
        self.state["current_condition_question"] = None
        # Rebuild tree so the sequence re-runs from MoveToPlace.
        self._rebuild_tree()
        return self.snapshot()

    # ── Logging ───────────────────────────────────────────────────────────────

    def record_recovery_decision(
        self, failure_type: str, chosen_recovery: str, reasoning: str
    ) -> None:
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

    # ── Tree interface ────────────────────────────────────────────────────────

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

    def get_condition_ids(self) -> Dict[str, Any]:
        """Return every condition ID used in the PlaceObject BT."""
        from .actions import LowerObject, MoveToPlace, ReleaseObject
        action_classes = [MoveToPlace, LowerObject, ReleaseObject]
        conditions: Dict[str, Any] = {}
        for action_class in action_classes:
            for phase, specs in [
                ("pre", getattr(action_class, "preconditions", ())),
                ("post", getattr(action_class, "postconditions", ())),
            ]:
                for spec in specs:
                    cid = spec.condition_id
                    if cid not in conditions:
                        conditions[cid] = {
                            "condition_id": cid,
                            "question": spec.question,
                            "failure_type_if_false": spec.failure_type,
                            "used_in": [],
                        }
                    conditions[cid]["used_in"].append(
                        {"action": action_class.__name__, "phase": phase}
                    )
        return {"conditions": list(conditions.values())}


def create_scripted_place_controller() -> PlaceObjectController:
    return PlaceObjectController(condition_provider=ScriptedConditionProvider())
