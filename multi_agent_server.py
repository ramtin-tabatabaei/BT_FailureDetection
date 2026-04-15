"""
Multi-Agent MCP Server  —  Pick-and-Place Behaviour Trees
==========================================================
Exposes three groups of tools corresponding to the three LLM agents in the
system:

    task_*      →  TaskExecutionAgent   drives both BTs and manages phases
    recovery_*  →  RecoveryAgent        decides recovery strategy on failure
    pick_*      →  shared BT tools for the PickObject phase
    place_*     →  shared BT tools for the PlaceObject phase

The 6 perception / monitoring agents (ScenePerceptionAgent,
GraspVerificationAgent, PoseVerificationAgent, ExecutionVerificationAgent,
TemporalMonitorAgent, InstantStateMonitorAgent) operate outside this server —
they inject failure signals via ``pick_set_failure`` / ``place_set_failure``
and their results are picked up by the FailureDetector classes inside the BT.

Architecture
------------
    ┌─────────────────────────────────────────────────────────┐
    │                    MCP Server                            │
    │                                                          │
    │  TaskExecutionAgent   (task_* tools)                     │
    │    drives tick loop, manages pick→place→done transitions │
    │                                                          │
    │  RecoveryAgent        (recovery_* tools)                 │
    │    called by TaskExecutionAgent on failure               │
    │    reasons about recovery strategy, applies choice       │
    │                                                          │
    │  pick_* / place_*  ← BT-specific tools used by both     │
    └─────────────────────────────────────────────────────────┘
         ▲  failure signals injected by external perception agents:
         │  ScenePerceptionAgent, GraspVerificationAgent,
         │  PoseVerificationAgent, ExecutionVerificationAgent,
         │  TemporalMonitorAgent, InstantStateMonitorAgent

Run::

    python multi_agent_server.py
"""
from __future__ import annotations

import sys
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("FastMCP not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

from orchestrator import PickAndPlaceOrchestrator

# ── Shared orchestrator (owns both BT controllers) ────────────────────────────

_orch = PickAndPlaceOrchestrator()
mcp = FastMCP("pickandplace-multiagent")


# ════════════════════════════════════════════════════════════════════════════════
# TaskExecutionAgent tools  (task_*)
# Drives the BT tick loop and manages phase transitions.
# Does NOT make recovery decisions — delegates those to RecoveryAgent.
# ════════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def task_get_summary() -> Dict[str, Any]:
    """Return a high-level snapshot of the overall pick-and-place task.

    Includes current phase, tick counts, success flags, and last failure
    for both the pick and place phases.  Call this first to orient yourself.
    """
    return _orch.get_task_summary()


@mcp.tool()
def task_tick_current() -> Dict[str, Any]:
    """Advance whichever BT phase is active by one tick.

    Automatically transitions pick → place when pick succeeds,
    and place → done when place succeeds.
    Returns phase, world_state, and tree_status.
    """
    return _orch.tick_current()


@mcp.tool()
def task_advance_phase() -> Dict[str, Any]:
    """Manually advance the task from the current phase to the next.

    Use when you want explicit control over the pick → place handoff
    rather than waiting for an automatic transition.
    """
    return _orch.advance_phase()


@mcp.tool()
def task_abort(reason: str = "agent_requested") -> Dict[str, Any]:
    """Abort the entire task and mark it as failed.

    Call when recovery is exhausted or the task cannot continue.
    """
    return _orch.abort(reason)


@mcp.tool()
def task_reset_all() -> Dict[str, Any]:
    """Reset both BT controllers and restart from the pick phase."""
    return _orch.reset_all()


@mcp.tool()
def task_get_combined_log() -> Dict[str, Any]:
    """Return the merged tick-history from both PickObject and PlaceObject BTs.

    Each entry is tagged with ``"agent": "pick"`` or ``"agent": "place"``.
    Use this at the end of an experiment for full execution analysis.
    """
    return {"combined_history": _orch.get_combined_history()}


@mcp.tool()
def task_describe_architecture() -> str:
    """Describe the full 8-agent architecture and this server's tool groups."""
    return """\
Multi-Agent Pick-and-Place BT System  —  8 Agents
===================================================

Perception / Monitoring Agents  (inject signals via pick_set_failure / place_set_failure)
  ScenePerceptionAgent      VLM           object_not_found
  GraspVerificationAgent    VLM           wrong_object_selection
  PoseVerificationAgent     cheap → VLM   wrong_position, wrong_orientation
  ExecutionVerificationAgent cheap → VLM  execution_mismatch
  TemporalMonitorAgent      cheap → VLM   freezing, action_timeout        (image sequence)
  InstantStateMonitorAgent  cheap → VLM   grip_loss, collision,           (single frame)
                                          force_limit_exceeded            (sensor only)

LLM Agents  (this MCP server)
  TaskExecutionAgent   task_*      drives tick loop, manages pick→place→done
  RecoveryAgent        recovery_*  decides and applies recovery on failure

Typical loop
------------
  task_get_summary          → check phase
  pick_describe_tree        → understand BT
  pick_set_conditions({..}) → inject scenario
  task_tick_current (loop)  → drive BT, observe state
    └─ on FAILURE → recovery_get_context → recovery_apply
  task_advance_phase        → once pick succeeds
  task_tick_current (loop)  → drive place BT
  task_get_combined_log     → full experiment record
"""


# ════════════════════════════════════════════════════════════════════════════════
# RecoveryAgent tools  (recovery_*)
# Specialises in failure diagnosis and recovery strategy selection.
# Called by TaskExecutionAgent after a tick returns FAILURE.
# ════════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def recovery_get_context(phase: str, failure_type: str) -> Dict[str, Any]:
    """Return full recovery context for the current failure.

    ``phase`` is ``"pick"`` or ``"place"``.
    Returns available recovery options, retry count, budget remaining,
    and the last few tick history entries so the RecoveryAgent has the
    context it needs to reason about the right strategy.
    """
    controller = _orch.pick_controller if phase == "pick" else _orch.place_controller
    context = controller.get_recovery_context(failure_type)

    # Include recent tick history so RecoveryAgent can see failure patterns.
    history = controller.state.get("tick_history", [])
    context["recent_history"] = history[-5:] if len(history) > 5 else history
    context["phase"] = phase
    return context


@mcp.tool()
def recovery_apply(
    phase: str,
    failure_type: str,
    chosen_recovery: str,
    reasoning: str,
) -> Dict[str, Any]:
    """Apply a recovery decision and resume BT execution.

    ``phase``            — ``"pick"`` or ``"place"``
    ``failure_type``     — the failure from world_state["last_failure"]
    ``chosen_recovery``  — one of the options from recovery_get_context
    ``reasoning``        — explanation of why this recovery fits this failure

    Records the reasoning in tick_history, increments retry count, and
    resets the BT to continue from the appropriate step.
    """
    controller = _orch.pick_controller if phase == "pick" else _orch.place_controller
    return controller.apply_recovery_choice(failure_type, chosen_recovery, reasoning)


@mcp.tool()
def recovery_get_history() -> Dict[str, Any]:
    """Return all recovery decisions made across both BTs in this session.

    Useful for the RecoveryAgent to review its own past decisions and
    avoid repeating failed strategies.
    """
    def extract_decisions(history, phase):
        return [
            {"phase": phase, **entry["recovery_decision"]}
            for entry in history
            if entry.get("recovery_decision")
        ]

    pick_history = _orch.pick_controller.state.get("tick_history", [])
    place_history = _orch.place_controller.state.get("tick_history", [])

    return {
        "recovery_decisions": (
            extract_decisions(pick_history, "pick")
            + extract_decisions(place_history, "place")
        )
    }


# ════════════════════════════════════════════════════════════════════════════════
# PickObject BT tools  (pick_*)
# Used by TaskExecutionAgent to inspect and configure the pick phase.
# ════════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def pick_describe_tree() -> str:
    """Return a unicode diagram of the PickObject behaviour tree."""
    return _orch.pick_controller.describe_tree()


@mcp.tool()
def pick_reset() -> Dict[str, Any]:
    """Reset the PickObject BT and world-state to initial values."""
    _orch.pick_controller.reset()
    if _orch.phase == "place":
        _orch.phase = "pick"
    return _orch.pick_controller.snapshot()


@mcp.tool()
def pick_get_condition_ids() -> Dict[str, Any]:
    """List every condition ID in the PickObject BT with its question and failure type."""
    from pickobject.actions import (
        CloseGripper, ComputeGraspPose, LiftObject, MoveToGrasp, MoveToPreGrasp,
    )
    action_classes = [ComputeGraspPose, MoveToPreGrasp, MoveToGrasp, CloseGripper, LiftObject]
    conditions: Dict[str, Any] = {}
    for action_class in action_classes:
        for phase, specs in [
            ("pre",  getattr(action_class, "preconditions",  ())),
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
def pick_set_condition(condition_id: str, value: bool) -> Dict[str, Any]:
    """Set a single PickObject condition (defaults to True; only set ones you want to fail)."""
    _orch.pick_controller.set_condition_response(condition_id, value)
    return _orch.pick_controller.snapshot()


@mcp.tool()
def pick_set_conditions(conditions: Dict[str, bool]) -> Dict[str, Any]:
    """Set multiple PickObject conditions in one call."""
    for cid, value in conditions.items():
        _orch.pick_controller.set_condition_response(cid, value)
    return _orch.pick_controller.snapshot()


@mcp.tool()
def pick_set_failure(
    failure_type: str, detected: bool, subtype: Optional[str] = None
) -> Dict[str, Any]:
    """Inject a failure signal into the PickObject BT.

    Called by perception/monitoring agents to relay their detection result.
    The corresponding FailureDetector inside the BT will pick this up on
    the next tick.
    """
    details: Dict[str, Any] = {}
    if subtype is not None:
        details["subtype"] = subtype
    _orch.pick_controller.set_agent_input(failure_type, detected, **details)
    return _orch.pick_controller.snapshot()


@mcp.tool()
def pick_get_state() -> Dict[str, Any]:
    """Return the current PickObject world-state snapshot (no tick)."""
    return _orch.pick_controller.snapshot()


@mcp.tool()
def pick_get_tick_history() -> Dict[str, Any]:
    """Return the full per-tick log for the PickObject BT."""
    return {"tick_history": _orch.pick_controller.state.get("tick_history", [])}


# ════════════════════════════════════════════════════════════════════════════════
# PlaceObject BT tools  (place_*)
# Used by TaskExecutionAgent to inspect and configure the place phase.
# ════════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def place_describe_tree() -> str:
    """Return a unicode diagram of the PlaceObject behaviour tree."""
    return _orch.place_controller.describe_tree()


@mcp.tool()
def place_reset() -> Dict[str, Any]:
    """Reset the PlaceObject BT and world-state to initial values."""
    _orch.place_controller.reset()
    return _orch.place_controller.snapshot()


@mcp.tool()
def place_get_condition_ids() -> Dict[str, Any]:
    """List every condition ID in the PlaceObject BT with its question and failure type."""
    return _orch.place_controller.get_condition_ids()


@mcp.tool()
def place_set_condition(condition_id: str, value: bool) -> Dict[str, Any]:
    """Set a single PlaceObject condition (defaults to True)."""
    _orch.place_controller.set_condition_response(condition_id, value)
    return _orch.place_controller.snapshot()


@mcp.tool()
def place_set_conditions(conditions: Dict[str, bool]) -> Dict[str, Any]:
    """Set multiple PlaceObject conditions in one call."""
    for cid, value in conditions.items():
        _orch.place_controller.set_condition_response(cid, value)
    return _orch.place_controller.snapshot()


@mcp.tool()
def place_set_failure(
    failure_type: str, detected: bool, subtype: Optional[str] = None
) -> Dict[str, Any]:
    """Inject a failure signal into the PlaceObject BT (from a perception agent)."""
    details: Dict[str, Any] = {}
    if subtype is not None:
        details["subtype"] = subtype
    _orch.place_controller.set_agent_input(failure_type, detected, **details)
    return _orch.place_controller.snapshot()


@mcp.tool()
def place_get_state() -> Dict[str, Any]:
    """Return the current PlaceObject world-state snapshot (no tick)."""
    return _orch.place_controller.snapshot()


@mcp.tool()
def place_get_tick_history() -> Dict[str, Any]:
    """Return the full per-tick log for the PlaceObject BT."""
    return {"tick_history": _orch.place_controller.state.get("tick_history", [])}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
