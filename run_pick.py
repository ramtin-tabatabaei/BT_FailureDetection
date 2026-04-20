"""Run the PickObject BT with only the real ScenePerceptionAgent active.

All conditions other than TargetVisible default to True (pass) because
ScriptedConditionProvider returns True for anything not explicitly set.
Only TargetVisible is evaluated by a real VLM call.

Usage:
    python run_pick.py                          # uses robot_detected.jpg
    python run_pick.py path/to/image.jpg        # custom image
    python run_pick.py image.jpg "red mug"      # custom image + target description
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
image_path = sys.argv[1] if len(sys.argv) > 1 else "robot_detected.jpg"
target_description = sys.argv[2] if len(sys.argv) > 2 else "target object for grasping"

if not Path(image_path).exists():
    print(f"[ERROR] Image not found: {image_path}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Controller — scripted so all other conditions default to True
# ---------------------------------------------------------------------------
from pickobject.controller import create_scripted_controller

controller = create_scripted_controller()

print("=" * 60)
print("  PickObject — real ScenePerceptionAgent, all others scripted")
print("=" * 60)
print(f"  image  : {image_path}")
print(f"  target : {target_description}")
print()

# ---------------------------------------------------------------------------
# Step 1: real VLM call for TargetVisible
# ---------------------------------------------------------------------------
print("── ScenePerceptionAgent  ·  TargetVisible ──────────────────")
try:
    from agents.scene_perception_agent import ScenePerceptionAgent
    agent = ScenePerceptionAgent()
    visible, explanation = agent.check(image_path, target_description)
    print(f"  ANSWER: {'YES' if visible else 'NO'}")
    print(f"  REASON: {explanation}")
except RuntimeError as exc:
    print(f"  [WARN] VLM unavailable ({exc}) — falling back to True")
    visible = True
    explanation = "Simulated: target object visible (no API key)."
    print(f"  REASON: {explanation}")

print()

# ---------------------------------------------------------------------------
# Step 2: inject result into controller
# ---------------------------------------------------------------------------
controller.set_condition_response("TargetVisible", visible)
print(f"  → TargetVisible = {visible}")
print()

# ---------------------------------------------------------------------------
# Step 3: tick the BT once
# ---------------------------------------------------------------------------
print("── BT tick ─────────────────────────────────────────────────")
state = controller.tick_once()

import py_trees
import json

print(py_trees.display.unicode_tree(controller.root, show_status=True))
print()

if state.get("last_failure"):
    print(f"  FAILURE : {state['last_failure']}")
elif state.get("pick_succeeded"):
    print("  SUCCESS : pick_succeeded = True")
else:
    tree_status = state.get("tick_history", [{}])[-1].get("tree_status", "UNKNOWN")
    print(f"  STATUS  : {tree_status}")

print()
print("── Conditions checked this tick ────────────────────────────")
for entry in state.get("tick_history", [{}])[-1].get("conditions_checked", []):
    status = "✓" if entry.get("result") else ("✗" if entry.get("result") is False else "–")
    print(f"  [{status}] {entry['condition_id']:30s}  phase={entry.get('phase','?'):4s}  step={entry.get('bt_step','?')}")

print()
print("=" * 60)
