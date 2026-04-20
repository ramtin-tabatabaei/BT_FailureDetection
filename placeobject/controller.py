from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional

import py_trees

from .failure_manager import PlaceFailureDetectorManager
from .failures import FAILURE_CONFIG, RUNTIME_FAILURE_TYPES

# Re-use the generic provider classes from pickobject — they are not
# pickobject-specific.
from pickobject.providers import (
    NullActionMonitor,
    ScriptedConditionProvider,
)


def build_initial_world_state() -> Dict[str, Any]:
    return {
        "place_location_visible": None,
        "object_secured_in_gripper": None,
        "at_place_location": None,
        "object_at_place_height": None,
        "placement_confirmed": None,
        "place_succeeded": False,
        "last_failure": None,
        "last_failure_subtype": None,
        "recovery_action": None,
        "retry_counts": {},
        "current_bt_step": "Idle",
        "current_condition_name": None,
        "current_condition_phase": None,
        "current_condition_question": None,
        "last_recovery_options": [],
        "last_recovery_budget": None,
        "agent_inputs": {},
        "tick_count": 0,
        "tick_history": [],
    }


@dataclass
class PlaceObjectController:
    """BT controller for the PlaceObject task.

    Mirrors the interface of :class:`pickobject.controller.PickObjectController`
    so that MCP tool implementations and agents work uniformly across both tasks.
    """

    condition_provider: Any
    failure_manager: PlaceFailureDetectorManager = field(
        default_factory=PlaceFailureDetectorManager
    )
    action_monitor: Any = field(default_factory=NullActionMonitor)
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
        self.failure_manager.selector.reload()
        self._rebuild_tree()

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(self.state)

    def set_condition_response(self, check_name: str, value: bool) -> None:
        if not hasattr(self.condition_provider, "set_response"):
            raise RuntimeError("Active condition provider does not support scripted responses")
        self.condition_provider.set_response(check_name, value)

    def set_agent_input(self, failure_type: str, detected: bool, **details: Any) -> None:
        """Inject a runtime failure signal from an external agent."""
        self.state.setdefault("agent_inputs", {})[failure_type] = {
            "detected": detected,
            **details,
        }

    # ── BT step / condition tracking ─────────────────────────────────────────

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

    _CONDITION_STATE_MAP: ClassVar[Dict[str, str]] = {
        "PlaceLocationVisible":    "place_location_visible",
        "ObjectSecuredInGripper":  "object_secured_in_gripper",
        "AtPlaceLocation":         "at_place_location",
        "ObjectAtPlaceHeight":     "object_at_place_height",
        "PlacementConfirmed":      "placement_confirmed",
    }

    def check(self, check_name: str, description: str) -> bool:
        result = self.condition_provider.check(check_name, description, self.state)

        # Write result back into world_state so it reflects what the BT observed.
        state_key = self._CONDITION_STATE_MAP.get(check_name)
        if state_key is not None:
            self.state[state_key] = result

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

    # ── Failure handling ──────────────────────────────────────────────────────

    def detect_failure(
        self, candidates: List[str], fallback: Optional[str] = None
    ) -> Optional[str]:
        """Check detectors for the first triggered failure in candidates."""
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

    def poll_runtime_failure(
        self, candidates: Optional[List[str]] = None
    ) -> Optional[str]:
        """Poll continuously-monitored failures during action execution."""
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

    def clear_failure(self) -> None:
        self.state["last_failure"] = None
        self.state["last_failure_subtype"] = None

    def set_action_failure(
        self, failure_type: str, subtype: Optional[str] = None
    ) -> py_trees.common.Status:
        self.state["last_failure"] = failure_type
        self.state["last_failure_subtype"] = subtype
        return py_trees.common.Status.FAILURE

    # ── Recovery ─────────────────────────────────────────────────────────────

    def get_failure_recoveries(self, failure_type: str) -> List[str]:
        return list(FAILURE_CONFIG.get(failure_type, {}).get("recoveries", []))

    def get_failure_retry_budget(self, failure_type: str) -> int:
        return int(FAILURE_CONFIG.get(failure_type, {}).get("retry_budget", 1))

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

    def apply_recovery_choice(
        self,
        failure_type: str,
        chosen_recovery: str,
        reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply a recovery decision and restart the PlaceObject BT from MoveToPlace."""
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
        # Rebuild tree so the sequence restarts from MoveToPlace.
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
    return PlaceObjectController(
        condition_provider=ScriptedConditionProvider(),
        failure_manager=PlaceFailureDetectorManager(),
        action_monitor=NullActionMonitor(),
    )
