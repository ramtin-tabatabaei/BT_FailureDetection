from __future__ import annotations

import json
import os
from pathlib import Path

from .failures import HOTKEY_FAILURE_TYPES, build_hotkey_hint

PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PACKAGE_ROOT / "configs"
CONFIG_PATH = CONFIG_DIR / "PickObject_failures_fixed.json"
SCENE_CONFIG_PATH = CONFIG_DIR / "PickObject_scene.json"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)
with SCENE_CONFIG_PATH.open("r", encoding="utf-8") as f:
    SCENE_CONFIG = json.load(f)

# ---------------------------------------------------------------------------
# Camera → image-path mapping
# Each condition_id's image_source resolves here to a real file path.
# Override any entry with an actual camera feed path for your hardware setup.
# ---------------------------------------------------------------------------
_IMAGES_DIR = PACKAGE_ROOT.parent / "Images"

# ---------------------------------------------------------------------------
# Target object description — used by all VLM agents as the grasp target.
# ---------------------------------------------------------------------------
TARGET_OBJECT = "red cube on the table"

# ---------------------------------------------------------------------------
# Place target description — the surface/location where the object is placed.
# ---------------------------------------------------------------------------
PLACE_TARGET = "red plate on the table"

# ---------------------------------------------------------------------------
# Active agents — controls which agents actually run condition checks.
# Add or remove names to enable/disable an agent across all BT actions.
# Available: ScenePerceptionAgent, GraspVerificationAgent,
#            PoseVerificationAgent, ExecutionVerificationAgent,
#            InstantStateMonitorAgent, TemporalMonitorAgent
# ---------------------------------------------------------------------------
ACTIVE_AGENTS: set[str] = {
    "ScenePerceptionAgent",
    # "GraspVerificationAgent",
    # "PoseVerificationAgent",
    # "ExecutionVerificationAgent",
    # "InstantStateMonitorAgent",
    # "TemporalMonitorAgent",
}

# ---------------------------------------------------------------------------
# Active detectors — controls which detectors run condition checks.
# Available: ObjectNotFoundDetector, WrongObjectSelectionDetector,
#            WrongPositionDetector, WrongOrientationDetector,
#            ExecutionMismatchDetector, FreezingDetector, GripLossDetector,
#            CollisionDetector, ForceLimitExceededDetector, ActionTimeoutDetector
# ---------------------------------------------------------------------------
ACTIVE_DETECTORS: set[str] = {
    # "ObjectNotFoundDetector",
    # "WrongObjectSelectionDetector",
    # "WrongPositionDetector",
    # "WrongOrientationDetector",
    # "ExecutionMismatchDetector",
    # "FreezingDetector",
    # "GripLossDetector",
    # "CollisionDetector",
    # "ForceLimitExceededDetector",
    # "ActionTimeoutDetector",
}

CAMERA_IMAGE_MAP: dict[str, str] = {
    "scene_camera":   str(_IMAGES_DIR / "scene_camera.png"),
    "wrist_camera":   "",   # set to wrist image filename inside Images/
    "gripper_camera": "",   # set to gripper image filename inside Images/
}

TASK_NAME = "PickObject"
TASK_CONFIG = CONFIG[TASK_NAME]
TASK_SCENE_CONFIG = SCENE_CONFIG[TASK_NAME]
FAILURE_CONFIG = TASK_CONFIG["failures"]
RECOVERY_CONFIG = TASK_CONFIG.get("recoveries", {})
DEFAULT_RETRY_BUDGET = TASK_CONFIG.get("default_retry_budget", 1)
ACTION_DURATION_SECONDS = float(os.environ.get("BT_ACTION_DURATION_SECONDS", "5"))
TICK_PERIOD_SECONDS = float(os.environ.get("BT_TICK_PERIOD_SECONDS", "2"))
MAX_TICKS = int(os.environ.get("BT_MAX_TICKS", "100"))

# Optional manual override for terminal-mode experiments.
ACTION_HOTKEY_FAILURES = HOTKEY_FAILURE_TYPES
ACTION_HOTKEY_HINT = build_hotkey_hint(ACTION_HOTKEY_FAILURES)
