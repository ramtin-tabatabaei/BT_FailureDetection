# PickObject Package

`pickobject` is the full pick-side behaviour-tree package.

It contains:

- the pick controller
- the pick BT
- action nodes and condition definitions
- failure configuration
- detector relays
- task-specific agent wrappers
- an interactive terminal mode
- a pick-only MCP server

This is the most complete package in the repository and is the best reference when adding new conditions, failures, agents, or detectors.

## What the Pick BT Does

The pick sequence is defined in `pickobject/tree.py`:

1. `ComputeGraspPose`
2. `MoveToPreGrasp`
3. `MoveToGrasp`
4. `CloseGripper`
5. `LiftObject`

When `LiftObject.on_conditions_satisfied()` runs, it sets `pick_succeeded = True`.

## Core File Map

### Package entry and public API

- `pickobject/__init__.py`: exports `build_mcp_server` and `main`.
- `pickobject/__main__.py`: allows `python -m pickobject`.
- `pickobject/main.py`: interactive CLI plus pick-only MCP server.

### Configuration and metadata

- `pickobject/config.py`: central pick configuration.
  - loads `PickObject_failures_fixed.json`
  - loads `PickObject_scene.json`
  - defines `CAMERA_IMAGE_MAP`
  - defines `TARGET_OBJECT`
  - defines `PLACE_TARGET`
  - defines `ACTIVE_AGENTS`
  - defines `ACTIVE_DETECTORS`
- `pickobject/failures.py`: runtime failure flags and hotkey mapping.
- `pickobject/configs/PickObject_failures_fixed.json`: retry budgets and allowed recoveries per failure.
- `pickobject/configs/PickObject_scene.json`: scene metadata and diagnosis prompt metadata.

### Controller and BT

- `pickobject/controller.py`: the main state machine for the pick BT.
  - stores world state
  - ticks the tree
  - logs checked conditions
  - records failures
  - manages recovery and resume step selection
  - provides `create_scripted_controller()` and `create_interactive_controller()`
- `pickobject/tree.py`: builds the pick sequence from `PICK_SEQUENCE`.
- `pickobject/providers.py`: terminal/scripted condition providers and action monitor classes.

### Failure handling

- `pickobject/failure_manager.py`: owns detector instances and returns the first active failure signal.
- `pickobject/experiment.py`: failure selector, enabled by default for every configured failure.
- `pickobject/detectors/base.py`: shared base class for pick detectors.
- `pickobject/detectors/__init__.py`: detector registry.

### Action definitions

- `pickobject/actions/base.py`: `ConditionSpec`, `failure_check`, `InstantAction`, `TimedInterruptibleAction`.
- `pickobject/actions/compute_grasp_pose.py`
- `pickobject/actions/move_to_pregrasp.py`
- `pickobject/actions/move_to_grasp.py`
- `pickobject/actions/close_gripper.py`
- `pickobject/actions/lift_object.py`
- `pickobject/actions/open_gripper.py`
- `pickobject/actions/__init__.py`

### Agent wrappers

- `pickobject/agents/base.py`: metadata base class for pick wrappers.
- `pickobject/agents/__init__.py`: registry of pick agent wrappers.
- `pickobject/agents/pick_scene_perception_agent.py`
- `pickobject/agents/pick_grasp_verification_agent.py`
- `pickobject/agents/pick_pose_verification_agent.py`
- `pickobject/agents/pick_execution_verification_agent.py`
- `pickobject/agents/pick_temporal_monitor_agent.py`
- `pickobject/agents/pick_instant_state_monitor_agent.py`
- `pickobject/agents/pick_task_execution_agent.py`
- `pickobject/agents/pick_recovery_agent.py`

## How the Pick Files Connect

The main connection path is:

1. `pickobject/tree.py` builds the action sequence.
2. Each action file declares `preconditions`, `hold_conditions`, and `postconditions`.
3. Each condition is a `ConditionSpec` created by `failure_check(...)`.
4. `ConditionSpec.should_check()` checks `ACTIVE_AGENTS` and `ACTIVE_DETECTORS` from `pickobject/config.py`.
5. If the condition is active, `PickObjectController.check()` asks the active provider for a boolean result.
6. If the condition fails, `PickObjectController.detect_failure()` asks `FailureDetectorManager` for a failure.
7. Recovery options come from `pickobject/configs/PickObject_failures_fixed.json`.
8. `apply_recovery_choice()` increments retry counts and resumes from the configured or current BT step.

## Pick Actions and Their Conditions

### `compute_grasp_pose.py`

- action type: `InstantAction`
- preconditions:
  - `TargetVisible`
  - failure type: `object_not_found`
  - agent: `ScenePerceptionAgent`
- purpose: do not compute a grasp unless the object is visible

### `move_to_pregrasp.py`

- action type: `TimedInterruptibleAction`
- preconditions:
  - `TargetVisible`
  - failure type: `object_not_found`
  - agent: `ScenePerceptionAgent`
  - detector: `ObjectNotFoundDetector`
  - `GripperReadyBeforeGrasp`
  - failure type: `execution_mismatch`
  - agent: `ExecutionVerificationAgent`
  - detector: `ExecutionMismatchDetector`
- hold conditions:
  - `GripperReadyBeforeGrasp`
- postconditions:
  - `GripperReadyBeforeGrasp`

### `move_to_grasp.py`

- action type: `TimedInterruptibleAction`
- preconditions:
  - `PreGraspPoseConfirmed`
  - failure type: `execution_mismatch`
  - agent: `ExecutionVerificationAgent`
  - detector: `ExecutionMismatchDetector`
  - `GripperReadyBeforeGrasp`
  - failure type: `execution_mismatch`
  - agent: `ExecutionVerificationAgent`
  - detector: `ExecutionMismatchDetector`
- hold conditions:
  - `GripperReadyBeforeGrasp`

### `close_gripper.py`

- action type: `TimedInterruptibleAction`
- preconditions:
  - `GripperReady`
  - failure type: `execution_mismatch`
  - agent: `ExecutionVerificationAgent`
  - detector: `ExecutionMismatchDetector`
  - `CorrectObjectSelected`
  - failure type: `wrong_object_selection`
  - agent: `GraspVerificationAgent`
  - detector: `WrongObjectSelectionDetector`
  - `GraspPositionAligned`
  - failure type: `wrong_position`
  - agent: `PoseVerificationAgent`
  - detector: `WrongPositionDetector`
  - `GraspOrientationAligned`
  - failure type: `wrong_orientation`
  - agent: `PoseVerificationAgent`
  - detector: `WrongOrientationDetector`
- postconditions:
  - `ObjectInGripper`
  - failure type: `grip_loss`
  - agent: `InstantStateMonitorAgent`
  - detector: `GripLossDetector`

### `lift_object.py`

- action type: `TimedInterruptibleAction`
- preconditions:
  - `ObjectInGripper`
  - failure type: `grip_loss`
  - agent: `InstantStateMonitorAgent`
  - detector: `GripLossDetector`
- hold conditions:
  - `ObjectInGripper`
- postconditions:
  - `FinalObjectInGripperCheck`
  - failure type: `grip_loss`
  - agent: `InstantStateMonitorAgent`
  - detector: `GripLossDetector`
- success hook:
  - sets `pick_succeeded = True`

### `open_gripper.py`

- scaffold action
- defined but not currently used by `PICK_SEQUENCE`

## Pick Agents

Pick agent wrappers live in `pickobject/agents/` and only add task-specific metadata plus light wrapper logic.

- `pick_scene_perception_agent.py`
  - name: `ScenePerceptionAgent`
  - owns `TargetVisible`
  - detects `object_not_found`
- `pick_grasp_verification_agent.py`
  - name: `GraspVerificationAgent`
  - owns `CorrectObjectSelected`
  - detects `wrong_object_selection`
- `pick_pose_verification_agent.py`
  - name: `PoseVerificationAgent`
  - owns `PreGraspPoseConfirmed`, `GraspPositionAligned`, `GraspOrientationAligned`
  - detects `wrong_position`, `wrong_orientation`, `execution_mismatch`
- `pick_execution_verification_agent.py`
  - name: `ExecutionVerificationAgent`
  - owns transition-level checks such as `GripperReady`, `GripperReadyBeforeGrasp`, `PreGraspPoseConfirmed`
  - detects `execution_mismatch`
- `pick_temporal_monitor_agent.py`
  - name: `TemporalMonitorAgent`
  - detects `freezing`, `action_timeout`
- `pick_instant_state_monitor_agent.py`
  - name: `InstantStateMonitorAgent`
  - owns grip/contact checks
  - detects `grip_loss`, `collision`, `force_limit_exceeded`, `execution_mismatch`
- `pick_task_execution_agent.py`
  - metadata wrapper for task execution role
- `pick_recovery_agent.py`
  - metadata wrapper for recovery role

## Pick Detectors

Each file in `pickobject/detectors/` is a small relay that reads `state["agent_inputs"][failure_type]`.

- `object_not_found_detector.py`: relays `object_not_found`
- `wrong_object_selection_detector.py`: relays `wrong_object_selection`
- `wrong_position_detector.py`: relays `wrong_position`
- `wrong_orientation_detector.py`: relays `wrong_orientation`
- `execution_mismatch_detector.py`: relays `execution_mismatch`
- `freezing_detector.py`: relays `freezing`
- `action_timeout_detector.py`: relays `action_timeout`
- `grip_loss_detector.py`: relays `grip_loss`
- `collision_detector.py`: relays `collision`
- `force_limit_exceeded_detector.py`: relays `force_limit_exceeded`

`pickobject/detectors/__init__.py` is the registry that maps each `failure_type` to its detector class.

## How To Turn Pick Agents On or Off

Edit `pickobject/config.py`.

Example:

```python
ACTIVE_AGENTS = {
    "ScenePerceptionAgent",
    "GraspVerificationAgent",
    "PoseVerificationAgent",
}
```

If an action condition names `ExecutionVerificationAgent`, but that name is not in `ACTIVE_AGENTS`, the condition is skipped unless its detector is still active.

## How To Turn Pick Detectors On or Off

Edit `pickobject/config.py`.

Example:

```python
ACTIVE_DETECTORS = {
    "ObjectNotFoundDetector",
    "WrongPositionDetector",
    "GripLossDetector",
}
```

If a condition's detector is not in `ACTIVE_DETECTORS`, it does not help activate that condition.

Important distinction:

- `ACTIVE_DETECTORS` gates condition execution.
- `ExperimentFailureSelector` in `pickobject/experiment.py` gates whether a failure type is globally enabled for the detector manager.

## How To Add a New Pick Failure

### Condition failure

1. Add it to `pickobject/configs/PickObject_failures_fixed.json`.
2. Add a `failure_check(...)` entry in the appropriate action.
3. If needed, add `agent_name` and `detector_name`.

### Runtime or injected failure

1. Add it to `pickobject/configs/PickObject_failures_fixed.json`.
2. Add it to `pickobject/failures.py` if it should be a runtime-polled or hotkey-mapped failure.
3. Add a detector file in `pickobject/detectors/`.
4. Register the detector in `pickobject/detectors/__init__.py`.
5. Inject the signal through `controller.set_agent_input(...)` or the MCP tool.

## How To Add a New Pick Agent

1. Create or update the shared implementation in `agents/`.
2. Add a wrapper in `pickobject/agents/`.
3. Register it in `pickobject/agents/__init__.py`.
4. Reference it by `agent_name` from an action condition.
5. Add its name to `ACTIVE_AGENTS`.

## How To Add a New Pick Detector

1. Create a new detector in `pickobject/detectors/`.
2. Subclass `FailureDetector`.
3. Set `failure_type`.
4. Register it in `pickobject/detectors/__init__.py`.
5. Add the detector name to `ACTIVE_DETECTORS`.

## Running PickObject

### Interactive terminal mode

```bash
python3 -m pickobject
```

This uses:

- `TerminalConditionProvider`
- `TerminalChoiceProvider`
- `InteractiveActionMonitor`

### Pick-only MCP mode

```bash
python3 -m pickobject --mcp
```

This uses:

- `ScriptedConditionProvider`
- `ScriptedChoiceProvider`
- `NullActionMonitor`

## Useful Pick MCP Tools

`pickobject/main.py` exposes:

- `describe_tree`
- `describe_agents`
- `find_responsible_agents`
- `reset_state`
- `set_condition`
- `set_conditions`
- `set_choice`
- `set_failure_agent_input`
- `get_enabled_failures`
- `get_recovery_options`
- `apply_recovery_choice`
- `tick_once`
- `get_state`
- `get_condition_ids`
- `record_recovery_decision`
- `get_tick_history`

## Key Implementation Notes

- pick is the reference implementation for this repository.
- hold conditions are supported in pick because `TimedInterruptibleAction.update()` reevaluates them during timed execution.
- pick runtime failures are also polled during timed execution.
- recovery resumption can jump to a configured step using `restart_step` or `resume_step` in the JSON config.
