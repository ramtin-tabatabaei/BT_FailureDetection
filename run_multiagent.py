#!/usr/bin/env python3
"""
run_multiagent.py  —  BT-driven pick-and-place with VLM failure detection
=========================================================================
The Behaviour Tree drives all execution. VLM agents are called once per
phase to evaluate conditions — no LLM orchestrator, no per-tick API calls.

Usage:
    python run_multiagent.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("BT_ACTION_DURATION_SECONDS", "3")
os.environ.setdefault("BT_TICK_PERIOD_SECONDS", "0")

# ── Config ────────────────────────────────────────────────────────────────────
from pickobject.config import ACTIVE_AGENTS, CAMERA_IMAGE_MAP, TARGET_OBJECT, PLACE_TARGET

def _img(source: str) -> str:
    return CAMERA_IMAGE_MAP.get(source, "")

def _agent_active(name: str) -> bool:
    return name in ACTIVE_AGENTS

# ── Orchestrator ──────────────────────────────────────────────────────────────
from orchestrator import PickAndPlaceOrchestrator
_orch = PickAndPlaceOrchestrator()

# ── Perception agents ─────────────────────────────────────────────────────────
from pickobject.agents import (
    PickScenePerceptionAgent,
    PickGraspVerificationAgent,
    PickPoseVerificationAgent,
    PickExecutionVerificationAgent,
    PickInstantStateMonitorAgent,
)
from placeobject.agents import (
    PlaceScenePerceptionAgent,
    PlaceGraspVerificationAgent,
    PlacePoseVerificationAgent,
    PlaceExecutionVerificationAgent,
    PlaceInstantStateMonitorAgent,
)

_pick_scene = PickScenePerceptionAgent()
_pick_grasp = PickGraspVerificationAgent()
_pick_pose  = PickPoseVerificationAgent()
_pick_exec  = PickExecutionVerificationAgent()
_pick_inst  = PickInstantStateMonitorAgent()

_place_scene = PlaceScenePerceptionAgent()
_place_grasp = PlaceGraspVerificationAgent()
_place_pose  = PlacePoseVerificationAgent()
_place_exec  = PlaceExecutionVerificationAgent()
_place_inst  = PlaceInstantStateMonitorAgent()

TARGET = TARGET_OBJECT

# Cache: (image_path, question) → (bool, reason) — never call same VLM twice
_vlm_cache: dict[tuple[str, str], tuple[bool, str]] = {}

def _cached_check(agent: Any, image_path: str, question: str) -> tuple[bool, str]:
    key = (image_path, question)
    if key not in _vlm_cache:
        _vlm_cache[key] = agent.check(image_path, question)
    return _vlm_cache[key]

def _skip(condition_id: str) -> tuple[bool, str]:
    return True, f"skipped ({condition_id} agent not active)"


# ── Perception runners ────────────────────────────────────────────────────────

def _run_pick_perception() -> dict[str, Any]:
    pic = _orch.pick_controller
    results: dict[str, Any] = {}
    scene_img = _img("scene_camera")
    wrist_img = _img("wrist_camera")

    # TargetVisible  ←  ScenePerceptionAgent
    if _agent_active("ScenePerceptionAgent"):
        visible, reason = _cached_check(_pick_scene, scene_img, TARGET)
    else:
        visible, reason = _skip("TargetVisible")
    pic.set_condition_response("TargetVisible", visible)
    results["TargetVisible"] = {"value": visible, "reason": reason}

    # CorrectObjectSelected  ←  GraspVerificationAgent
    if _agent_active("GraspVerificationAgent"):
        correct, reason = _pick_grasp.check(wrist_img, TARGET)
    else:
        correct, reason = _skip("CorrectObjectSelected")
    pic.set_condition_response("CorrectObjectSelected", correct)
    results["CorrectObjectSelected"] = {"value": correct, "reason": reason}

    # GraspPositionAligned / GraspOrientationAligned / PreGraspPoseConfirmed  ←  PoseVerificationAgent
    if _agent_active("PoseVerificationAgent"):
        g_pos, reason_pos = _pick_pose.check_position(position_error_mm=3.1, threshold_mm=5.0)
        g_ori, reason_ori = _pick_pose.check_orientation(angle_error_deg=1.8, threshold_deg=5.0)
        pre_ok, reason_pre = _pick_pose.check_position(position_error_mm=8.2, threshold_mm=15.0)
    else:
        g_pos, reason_pos = _skip("GraspPositionAligned")
        g_ori, reason_ori = _skip("GraspOrientationAligned")
        pre_ok, reason_pre = _skip("PreGraspPoseConfirmed")
    pic.set_condition_response("GraspPositionAligned", g_pos)
    pic.set_condition_response("GraspOrientationAligned", g_ori)
    pic.set_condition_response("PreGraspPoseConfirmed", pre_ok)
    results["GraspPositionAligned"]    = {"value": g_pos,  "reason": reason_pos}
    results["GraspOrientationAligned"] = {"value": g_ori,  "reason": reason_ori}
    results["PreGraspPoseConfirmed"]   = {"value": pre_ok, "reason": reason_pre}

    # GripperReadyBeforeGrasp / ObjectInGripper  ←  InstantStateMonitorAgent
    if _agent_active("InstantStateMonitorAgent"):
        grip_ok, reason_grip = _pick_inst.check_gripper_state(gripper_open=True, fault="none")
        in_grip, reason_ig   = _pick_inst.check_grip(force_n=12.4, slip_detected=False)
        final_grip, reason_fg = _pick_inst.check_grip(force_n=11.7, slip_detected=False)
    else:
        grip_ok, reason_grip = _skip("GripperReadyBeforeGrasp")
        in_grip, reason_ig   = _skip("ObjectInGripper")
        final_grip, reason_fg = _skip("FinalObjectInGripperCheck")
    pic.set_condition_response("GripperReadyBeforeGrasp", grip_ok)
    pic.set_condition_response("GripperReady", grip_ok)
    pic.set_condition_response("ObjectInGripper", in_grip)
    pic.set_condition_response("FinalObjectInGripperCheck", final_grip)
    results["GripperReadyBeforeGrasp"]   = {"value": grip_ok,    "reason": reason_grip}
    results["ObjectInGripper"]           = {"value": in_grip,    "reason": reason_ig}
    results["FinalObjectInGripperCheck"] = {"value": final_grip, "reason": reason_fg}

    return results


def _run_place_perception() -> dict[str, Any]:
    plc = _orch.place_controller
    results: dict[str, Any] = {}
    scene_img = _img("scene_camera")
    wrist_img = _img("wrist_camera")

    # PlaceLocationVisible  ←  ScenePerceptionAgent
    if _agent_active("ScenePerceptionAgent"):
        loc_vis, reason = _cached_check(_place_scene, scene_img, PLACE_TARGET)
    else:
        loc_vis, reason = _skip("PlaceLocationVisible")
    plc.set_condition_response("PlaceLocationVisible", loc_vis)
    results["PlaceLocationVisible"] = {"value": loc_vis, "reason": reason}

    # ObjectSecuredInGripper  ←  GraspVerificationAgent
    if _agent_active("GraspVerificationAgent"):
        secured, reason = _place_grasp.check(wrist_img, TARGET)
    else:
        secured, reason = _skip("ObjectSecuredInGripper")
    plc.set_condition_response("ObjectSecuredInGripper", secured)
    results["ObjectSecuredInGripper"] = {"value": secured, "reason": reason}

    # AtPlaceLocation / ObjectAtPlaceHeight  ←  PoseVerificationAgent
    if _agent_active("PoseVerificationAgent"):
        at_loc, reason_loc = _place_pose.check_position(position_error_mm=5.4, threshold_mm=10.0)
        at_h,   reason_h   = _place_pose.check_height(height_error_mm=1.2, threshold_mm=3.0)
    else:
        at_loc, reason_loc = _skip("AtPlaceLocation")
        at_h,   reason_h   = _skip("ObjectAtPlaceHeight")
    plc.set_condition_response("AtPlaceLocation", at_loc)
    plc.set_condition_response("ObjectAtPlaceHeight", at_h)
    results["AtPlaceLocation"]     = {"value": at_loc, "reason": reason_loc}
    results["ObjectAtPlaceHeight"] = {"value": at_h,   "reason": reason_h}

    # PlacementConfirmed  ←  ExecutionVerificationAgent
    if _agent_active("ExecutionVerificationAgent"):
        verification = _place_exec.check_transition(
            scene_img,
            current_action="ReleaseObject",
            current_post_conditions=[
                ("PlacementConfirmed",
                 "After releasing the object, is it resting stably on the placement surface?")
            ],
            predicted_answers={"PlacementConfirmed": True},
        )
        confirmed, reason = verification.all_satisfied, verification.summary
    else:
        confirmed, reason = _skip("PlacementConfirmed")
    plc.set_condition_response("PlacementConfirmed", confirmed)
    results["PlacementConfirmed"] = {"value": confirmed, "reason": reason}

    return results


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_perception(phase: str, results: dict[str, Any]) -> None:
    print(f"\n  [Perception] {phase} phase:")
    for cond, info in results.items():
        mark = "✓" if info["value"] else "✗"
        print(f"    {mark} {cond}: {info['reason']}")


def _tick_to_completion(max_ticks: int = 5000) -> dict[str, Any]:
    """Tick the active BT until SUCCESS or FAILURE. Pure Python — no API calls."""
    import time as _time
    last: dict[str, Any] = {}
    for _ in range(max_ticks):
        last = _orch.tick_current()
        status = last.get("tree_status", "")
        # py_trees returns "Status.SUCCESS" / "Status.FAILURE"
        if status.endswith("SUCCESS") or status.endswith("FAILURE"):
            break
        _time.sleep(0.05)
    return last


def _apply_recovery(phase: str, failure_type: str) -> bool:
    """Pick the first available recovery and apply it. Returns False if none left."""
    ctrl = _orch.pick_controller if phase == "pick" else _orch.place_controller
    ctx = ctrl.get_recovery_context(failure_type)

    options = ctx.get("recovery_options", [])
    retries = ctx.get("retries_remaining", 0)

    if retries <= 0 or not options:
        print(f"  [Recovery] No retries left for {failure_type}. Aborting.")
        return False

    chosen = options[0]  # take the first available option
    result = ctrl.apply_recovery_choice(failure_type, chosen, reasoning="auto-selected first option")
    print(f"  [Recovery] {failure_type} → applied '{chosen}': {result.get('message', '')}")
    return True


# ── Main execution loop ───────────────────────────────────────────────────────

def _run_phase(phase: str, run_perception: Any, max_retries: int = 3) -> bool:
    """Run one phase (pick or place). Returns True on success."""
    print(f"\n{'═'*60}")
    print(f"  Phase: {phase.upper()}")
    print(f"{'═'*60}")

    for attempt in range(1, max_retries + 2):
        # Run perception once before ticking
        print(f"\n  [Perception] Running agents... (attempt {attempt})")
        results = run_perception()
        _print_perception(phase, results)

        # Tick BT to completion — pure Python, no API calls
        print(f"\n  [BT] Ticking to completion...")
        outcome = _tick_to_completion()
        status = outcome.get("tree_status", "UNKNOWN")
        ticks  = outcome.get("tick_count", "?")
        print(f"  [BT] Status: {status}  (ticks: {ticks})")

        if status.endswith("SUCCESS"):
            return True

        # Handle failure
        failure = outcome.get("world_state", {}).get("last_failure")
        if not failure:
            print(f"  [BT] FAILURE with no detected failure type. Aborting.")
            return False

        print(f"  [BT] Failure detected: {failure}")
        if attempt > max_retries:
            print(f"  [Recovery] Max retries reached. Aborting.")
            return False

        if not _apply_recovery(phase, failure):
            return False

        # Clear VLM cache so perception re-runs fresh after recovery
        _vlm_cache.clear()

    return False


def main() -> None:
    W = 68
    print("█" * W)
    print("  Multi-Agent Pick-and-Place  —  BT-driven, VLM failure detection")
    print("█" * W)
    print(f"  scene_camera   : {_img('scene_camera') or '(not set)'}")
    print(f"  wrist_camera   : {_img('wrist_camera') or '(not set)'}")
    print(f"  gripper_camera : {_img('gripper_camera') or '(not set)'}")
    print(f"  active agents  : {sorted(ACTIVE_AGENTS) or '(none)'}")
    print()

    # ── Pick phase ────────────────────────────────────────────────────────────
    pick_ok = _run_phase("pick", _run_pick_perception)
    if not pick_ok:
        print("\n  [ABORT] Pick phase failed.")
        _orch.abort("pick_failed")
    else:
        print("\n  [OK] Pick succeeded. Advancing to place phase.")
        # Only advance if the orchestrator hasn't already auto-transitioned.
        if _orch.phase == "pick":
            _orch.advance_phase()

        # ── Place phase ───────────────────────────────────────────────────────
        place_ok = _run_phase("place", _run_place_perception)
        if not place_ok:
            print("\n  [ABORT] Place phase failed.")
            _orch.abort("place_failed")
        else:
            print("\n  [OK] Place succeeded.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "═" * W)
    summary = _orch.get_task_summary()
    print("  Final summary:")
    for k, v in summary.items():
        print(f"    {k}: {v}")
    print("═" * W)


if __name__ == "__main__":
    main()
