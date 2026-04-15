"""
PickAndPlaceOrchestrator
========================
Coordinates two BT controllers — PickObject and PlaceObject — as a two-phase
sequential task.  The orchestrator is the "brain" of the multi-agent system:

    Phase "pick"   → PickObjectController drives until pick_succeeded=True
    Phase "place"  → PlaceObjectController drives until place_succeeded=True
    Phase "done"   → full task complete
    Phase "failed" → unrecoverable failure at either phase

Each phase's BT is independently controlled by its own agent tools in the MCP
server (``pick_*`` / ``place_*``).  The orchestrator tools (``orch_*``) manage
phase transitions and provide a unified view of the whole task.
"""
from __future__ import annotations

from typing import Any, Dict, List

import py_trees

from pickobject.controller import PickObjectController, create_scripted_controller
from placeobject.controller import PlaceObjectController, create_scripted_place_controller

PHASES = ("pick", "place", "done", "failed")


class PickAndPlaceOrchestrator:
    """Owns one PickObjectController and one PlaceObjectController.

    The active phase determines which controller ``tick_current`` advances.
    Phase transitions happen automatically when a task succeeds, or can be
    triggered manually via ``advance_phase``.
    """

    def __init__(self) -> None:
        self.pick_controller: PickObjectController = create_scripted_controller()
        self.place_controller: PlaceObjectController = create_scripted_place_controller()
        self.phase: str = "pick"

    # ── Phase management ──────────────────────────────────────────────────────

    def _check_phase_transition(self) -> None:
        """Automatically advance phase when the current task completes."""
        if self.phase == "pick" and self.pick_controller.state.get("pick_succeeded"):
            self.phase = "place"
        elif self.phase == "place" and self.place_controller.state.get("place_succeeded"):
            self.phase = "done"

    def advance_phase(self) -> Dict[str, Any]:
        """Manually advance from pick → place (e.g. after confirming pick succeeded).

        Useful when the agent wants to transition phases without waiting for an
        automatic trigger.  Returns the new task summary.
        """
        if self.phase == "pick":
            self.phase = "place"
        elif self.phase == "place":
            self.phase = "done"
        return self.get_task_summary()

    def abort(self, reason: str = "agent_requested") -> Dict[str, Any]:
        """Mark the overall task as failed (unrecoverable)."""
        self.phase = "failed"
        return {"phase": self.phase, "reason": reason, **self.get_task_summary()}

    # ── Tick interface ────────────────────────────────────────────────────────

    def tick_current(self) -> Dict[str, Any]:
        """Advance whichever BT is currently active by one tick.

        After the tick, check whether a phase transition should fire.
        Returns a dict with ``phase``, ``world_state``, and ``tree_status``.
        """
        if self.phase == "pick":
            state = self.pick_controller.tick_once()
            tree_status = str(self.pick_controller.root.status)
        elif self.phase == "place":
            state = self.place_controller.tick_once()
            tree_status = str(self.place_controller.root.status)
        else:
            return {
                "phase": self.phase,
                "world_state": {},
                "tree_status": "IDLE",
                "message": f"Task already in terminal phase '{self.phase}'.",
            }

        self._check_phase_transition()

        return {
            "phase": self.phase,
            "world_state": state,
            "tree_status": tree_status,
        }

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset_all(self) -> Dict[str, Any]:
        """Reset both controllers and return to the pick phase."""
        self.pick_controller.reset()
        self.place_controller.reset()
        self.phase = "pick"
        return self.get_task_summary()

    # ── Observation ───────────────────────────────────────────────────────────

    def get_task_summary(self) -> Dict[str, Any]:
        """Return a high-level snapshot of overall task progress."""
        return {
            "phase": self.phase,
            "pick_ticks": self.pick_controller.state.get("tick_count", 0),
            "place_ticks": self.place_controller.state.get("tick_count", 0),
            "pick_succeeded": self.pick_controller.state.get("pick_succeeded", False),
            "place_succeeded": self.place_controller.state.get("place_succeeded", False),
            "pick_last_failure": self.pick_controller.state.get("last_failure"),
            "place_last_failure": self.place_controller.state.get("last_failure"),
            "pick_recovery_counts": self.pick_controller.state.get("retry_counts", {}),
            "place_recovery_counts": self.place_controller.state.get("retry_counts", {}),
        }

    def get_combined_history(self) -> List[Dict[str, Any]]:
        """Return tick-history entries from both BTs, tagged by agent.

        Each entry gets an ``"agent"`` key (``"pick"`` or ``"place"``) so the
        caller can reconstruct the full execution timeline.
        """
        pick_history = [
            {"agent": "pick", **entry}
            for entry in self.pick_controller.state.get("tick_history", [])
        ]
        place_history = [
            {"agent": "place", **entry}
            for entry in self.place_controller.state.get("tick_history", [])
        ]
        # Merge in chronological order (pick always runs first).
        return pick_history + place_history
