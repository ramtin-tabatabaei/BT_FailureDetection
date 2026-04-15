from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None

from .config import CONFIG_PATH, SCENE_CONFIG_PATH
from .controller import create_interactive_controller, create_scripted_controller


def build_mcp_server() -> Any:
    if FastMCP is None:
        raise RuntimeError("FastMCP is not installed. Install the 'mcp' package to run the MCP server.")

    controller = create_scripted_controller()
    mcp = FastMCP("pickobject")

    @mcp.tool()
    def describe_tree() -> str:
        return controller.describe_tree()

    @mcp.tool()
    def reset_state() -> Dict[str, Any]:
        controller.reset()
        if hasattr(controller.condition_provider, "clear"):
            controller.condition_provider.clear()
        if hasattr(controller.choice_provider, "clear"):
            controller.choice_provider.clear()
        return controller.snapshot()

    @mcp.tool()
    def set_condition(check_name: str, value: bool) -> Dict[str, Any]:
        controller.set_condition_response(check_name, value)
        return controller.snapshot()

    @mcp.tool()
    def set_choice(prompt_key: str, value: str) -> Dict[str, Any]:
        controller.set_choice_response(prompt_key, value)
        return controller.snapshot()

    @mcp.tool()
    def set_failure_agent_input(failure_type: str, detected: bool, subtype: Optional[str] = None) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        if subtype is not None:
            details["subtype"] = subtype
        controller.set_agent_input(failure_type, detected, **details)
        return controller.snapshot()

    @mcp.tool()
    def get_enabled_failures() -> Dict[str, Any]:
        return {
            "config_path": str(CONFIG_PATH),
            "enabled_failures": controller.failure_manager.enabled_failures(),
        }

    @mcp.tool()
    def get_recovery_options(failure_type: Optional[str] = None) -> Dict[str, Any]:
        current_failure = failure_type or controller.state.get("last_failure")
        if not current_failure:
            return {"failure_type": None, "recoveries": []}
        return controller.get_recovery_context(current_failure)

    @mcp.tool()
    def apply_recovery_choice(
        chosen_recovery: str,
        failure_type: Optional[str] = None,
        reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        current_failure = failure_type or controller.state.get("last_failure")
        if not current_failure:
            raise ValueError("No active failure is recorded for recovery selection.")
        controller.apply_recovery_choice(current_failure, chosen_recovery, reasoning)
        return controller.snapshot()

    @mcp.tool()
    def tick_once() -> Dict[str, Any]:
        """Advance the BT by one tick. Returns world state and tree status."""
        controller.tick_once()
        return {
            "world_state": controller.snapshot(),
            "tree": controller.describe_tree(),
        }

    @mcp.tool()
    def get_state() -> Dict[str, Any]:
        """Return the current world state snapshot."""
        return controller.snapshot()

    @mcp.tool()
    def get_condition_ids() -> Dict[str, Any]:
        """Return every condition ID checked during the PickObject BT.

        For each condition you get: its stable ``condition_id``, the question
        used to evaluate it, the failure type triggered when it returns False,
        and every (action, phase) pair where it appears.  Use this to know
        exactly which IDs to pass to ``set_condition`` or ``set_conditions``.
        """
        from .actions import (
            CloseGripper,
            ComputeGraspPose,
            LiftObject,
            MoveToGrasp,
            MoveToPreGrasp,
        )

        action_classes = [ComputeGraspPose, MoveToPreGrasp, MoveToGrasp, CloseGripper, LiftObject]
        conditions: Dict[str, Any] = {}
        for action_class in action_classes:
            for phase, specs in [
                ("pre", getattr(action_class, "preconditions", ())),
                ("hold", getattr(action_class, "hold_conditions", ())),
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

    @mcp.tool()
    def set_conditions(conditions: Dict[str, bool]) -> Dict[str, Any]:
        """Set multiple condition responses in one call.

        Pass a dict of ``{condition_id: True/False}``.  Conditions not
        listed here default to True (pass) because of the scripted provider
        default.  So you only need to set the ones you want to *fail*.

        Example: ``{"TargetVisible": False}`` simulates object-not-found while
        leaving all other conditions passing.
        """
        for check_name, value in conditions.items():
            controller.set_condition_response(check_name, value)
        return controller.snapshot()

    @mcp.tool()
    def record_recovery_decision(
        failure_type: str, chosen_recovery: str, reasoning: str
    ) -> Dict[str, Any]:
        """Record the agent's reasoning for a recovery decision.

        Call this *after* a tick returns a failure and *before* resetting or
        retrying.  The reasoning is attached to the last tick entry in
        ``tick_history`` so the full experiment log captures not just *what*
        happened but *why* each recovery was chosen.

        ``failure_type``     — the failure type from world_state[\"last_failure\"]
        ``chosen_recovery``  — the recovery strategy the agent decided on
        ``reasoning``        — free-text explanation of why this recovery fits
        """
        controller.record_recovery_decision(failure_type, chosen_recovery, reasoning)
        return controller.snapshot()

    @mcp.tool()
    def get_tick_history() -> Dict[str, Any]:
        """Return the full tick-by-tick experiment log.

        Each entry contains:
        - ``tick``               : tick index
        - ``conditions_checked`` : list of {condition_id, result, phase, bt_step}
        - ``failure_detected``   : {failure_type, subtype} or null
        - ``tree_status``        : py_trees status string (SUCCESS / FAILURE / RUNNING)
        - ``bt_step``            : last active BT step name
        - ``recovery_decision``  : {failure_type, chosen_recovery, reasoning} if recorded
        """
        return {"tick_history": controller.state.get("tick_history", [])}

    return mcp


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        build_mcp_server().run()
        return

    controller = create_interactive_controller()
    print(f"Loaded config from: {CONFIG_PATH}")
    print(f"Loaded scene config from: {SCENE_CONFIG_PATH}")
    print(controller.describe_tree())
    print("\nStarting interactive PickObject run.")
    print("You will be asked y/n for every condition check.\n")
    final_state = controller.run()
    print("\nFinal world_state:")
    print(json.dumps(final_state, indent=2))
