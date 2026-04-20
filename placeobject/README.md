# PlaceObject Package

`placeobject` is the place-side behaviour-tree package.

It contains:

- the place controller
- the place BT
- place actions
- place failure config
- place detector relays
- place-specific agent wrappers

It does not currently have a standalone `main.py` like `pickobject`.

## Current Status

`placeobject` is structurally complete, but several action-level condition checks are still scaffolded and commented out in the action files.

That means:

- the controller, tree, agents, detectors, and failure config exist
- the actions are present
- recovery exists
- but much of the condition-level wiring is not active yet

This package is best read as the place-side counterpart to `pickobject`, with some unfinished condition integration.

## What the Place BT Does

The place sequence is defined in `placeobject/tree.py`:

1. `MoveToPlace`
2. `LowerObject`
3. `ReleaseObject`

When `ReleaseObject.on_success()` runs, it sets `place_succeeded = True`.

## Core File Map

### Package entry and public API

- `placeobject/__init__.py`: exports `PlaceObjectController` and `create_scripted_place_controller`.

### Controller and BT

- `placeobject/controller.py`: place controller, state store, failure handling, recovery, tick logging, and condition inventory.
- `placeobject/tree.py`: builds the place sequence.
- `placeobject/experiment.py`: failure selector for place experiments.
- `placeobject/failure_manager.py`: detector manager for place failures.
- `placeobject/failures.py`: place failure rules and recovery configuration.

### Action definitions

- `placeobject/actions/base.py`: `ConditionSpec`, `failure_check`, `InstantPlaceAction`, `TimedPlaceAction`.
- `placeobject/actions/move_to_place.py`
- `placeobject/actions/lower_object.py`
- `placeobject/actions/release_object.py`
- `placeobject/actions/__init__.py`

### Agent wrappers

- `placeobject/agents/base.py`: metadata base class.
- `placeobject/agents/__init__.py`: registry of place wrappers.
- `placeobject/agents/place_scene_perception_agent.py`
- `placeobject/agents/place_grasp_verification_agent.py`
- `placeobject/agents/place_pose_verification_agent.py`
- `placeobject/agents/place_execution_verification_agent.py`
- `placeobject/agents/place_temporal_monitor_agent.py`
- `placeobject/agents/place_instant_state_monitor_agent.py`
- `placeobject/agents/place_task_execution_agent.py`
- `placeobject/agents/place_recovery_agent.py`

### Detectors

- `placeobject/detectors/base.py`: re-exports the shared detector base.
- `placeobject/detectors/__init__.py`: registry of place detector classes.
- `placeobject/detectors/placement_location_blocked_detector.py`
- `placeobject/detectors/object_dropped_detector.py`
- `placeobject/detectors/placement_misaligned_detector.py`
- `placeobject/detectors/collision_on_descent_detector.py`
- `placeobject/detectors/freezing_detector.py`
- `placeobject/detectors/action_timeout_detector.py`
- `placeobject/detectors/execution_mismatch_detector.py`

## How the Place Files Connect

The main place connection path is:

1. `placeobject/tree.py` creates the place action sequence.
2. Each place action inherits from `TimedPlaceAction`.
3. Conditions are declared with `failure_check(...)` in the action class.
4. `ConditionSpec.should_check()` in `placeobject/actions/base.py` decides whether the condition is active.
5. `PlaceObjectController.check()` evaluates the condition through `ScriptedConditionProvider`.
6. If a condition fails, `PlaceObjectController.detect_failure()` asks `PlaceFailureDetectorManager` to translate it into a `FailureSignal`.
7. Recovery options are read from `placeobject/failures.py`.

Important implementation detail:

`placeobject/actions/base.py` imports `ACTIVE_AGENTS` and `ACTIVE_DETECTORS` from `pickobject/config.py`, so place currently shares those toggles with pick.

## Place Actions and Their Current Wiring

### `move_to_place.py`

- action type: `TimedPlaceAction`
- intended checks:
  - `ObjectSecuredInGripper`
  - failure type: `object_dropped`
  - agent: `GraspVerificationAgent`
  - `PlaceLocationVisible`
  - failure type: `placement_location_blocked`
  - agent: `ScenePerceptionAgent`
  - post `AtPlaceLocation`
  - failure type: `placement_misaligned`
  - agent: `PoseVerificationAgent`
- current status:
  - these checks are present as commented `failure_check(...)` blocks
  - they are not currently active

### `lower_object.py`

- action type: `TimedPlaceAction`
- intended checks:
  - pre `AtPlaceLocation`
  - failure type: `placement_misaligned`
  - agent: `PoseVerificationAgent`
  - post `ObjectAtPlaceHeight`
  - failure type: `collision_on_descent`
  - agent: `PoseVerificationAgent`
- current status:
  - these checks are commented out

### `release_object.py`

- action type: `TimedPlaceAction`
- intended checks:
  - pre `ObjectAtPlaceHeight`
  - failure type: `collision_on_descent`
  - agent: `PoseVerificationAgent`
  - post `PlacementConfirmed`
  - failure type: `placement_misaligned`
  - agent: `ExecutionVerificationAgent`
- current status:
  - these checks are commented out
- active success hook:
  - `on_success()` sets `place_succeeded = True`

## Place Agents

The place wrappers describe ownership for the place-side conditions and failures.

- `place_scene_perception_agent.py`
  - name: `ScenePerceptionAgent`
  - owns `PlaceLocationVisible`
  - detects `placement_location_blocked`
- `place_grasp_verification_agent.py`
  - name: `GraspVerificationAgent`
  - owns `ObjectSecuredInGripper`
  - detects `object_dropped`
- `place_pose_verification_agent.py`
  - name: `PoseVerificationAgent`
  - owns `AtPlaceLocation` and `ObjectAtPlaceHeight`
  - detects `placement_misaligned`
- `place_execution_verification_agent.py`
  - name: `ExecutionVerificationAgent`
  - owns `PlacementConfirmed`
  - detects `execution_mismatch`
- `place_temporal_monitor_agent.py`
  - name: `TemporalMonitorAgent`
  - detects `freezing` and `action_timeout`
- `place_instant_state_monitor_agent.py`
  - name: `InstantStateMonitorAgent`
  - detects `object_dropped` and `collision_on_descent`
- `place_task_execution_agent.py`
  - metadata wrapper for task execution
- `place_recovery_agent.py`
  - metadata wrapper for recovery

## Place Detectors

Each place detector relays a named failure from `state["agent_inputs"]`.

- `placement_location_blocked_detector.py`: relays `placement_location_blocked`
- `object_dropped_detector.py`: relays `object_dropped`
- `placement_misaligned_detector.py`: relays `placement_misaligned`
- `collision_on_descent_detector.py`: relays `collision_on_descent`
- `freezing_detector.py`: relays `freezing`
- `action_timeout_detector.py`: relays `action_timeout`
- `execution_mismatch_detector.py`: relays `execution_mismatch`

`placeobject/detectors/__init__.py` maps each `failure_type` to its detector class.

## Place Failures

`placeobject/failures.py` contains:

- `FAILURE_RULES`
- `RUNTIME_FAILURE_TYPES`
- `FAILURE_CONFIG`

Configured failure types:

- `placement_location_blocked`
- `object_dropped`
- `placement_misaligned`
- `collision_on_descent`
- `freezing`
- `action_timeout`
- `execution_mismatch`

Unlike pick, place stores its recovery configuration directly in Python rather than JSON.

## How To Turn Place Agents On or Off

Place currently reuses the pick config toggles.

Edit `pickobject/config.py`:

```python
ACTIVE_AGENTS = {
    "ScenePerceptionAgent",
    "PoseVerificationAgent",
}
```

Because `placeobject/actions/base.py` imports these sets from `pickobject/config.py`, changing them affects place condition activation as well.

## How To Turn Place Detectors On or Off

Place also reuses `ACTIVE_DETECTORS` from `pickobject/config.py`.

Example:

```python
ACTIVE_DETECTORS = {
    "PlacementLocationBlockedDetector",
    "PlacementMisalignedDetector",
}
```

Important note:

- this only matters for active condition checks in place actions
- since many place action checks are still commented out, detector activation has less effect right now than it does in pick

## Runtime Monitoring Note for Place

`placeobject/failures.py` defines runtime-style failures such as:

- `object_dropped`
- `collision_on_descent`
- `freezing`
- `action_timeout`

However, `TimedPlaceAction.update()` does not currently poll `controller.poll_runtime_failure()` the way `pickobject/actions/base.py` does.

So the runtime failure scaffolding exists, but the runtime polling loop is not yet as complete as the pick side.

## How To Add a New Place Failure

1. Add it to `placeobject/failures.py`.
2. If it is a detector-driven failure, add a detector file in `placeobject/detectors/`.
3. Register that detector in `placeobject/detectors/__init__.py`.
4. Add or uncomment a `failure_check(...)` in the relevant place action.
5. If needed, add a place wrapper in `placeobject/agents/`.

## How To Add a New Place Agent

1. Create or update the shared implementation in `agents/`.
2. Add a wrapper in `placeobject/agents/`.
3. Register it in `placeobject/agents/__init__.py`.
4. Reference it by `agent_name` in a place action condition.
5. Add its name to `ACTIVE_AGENTS` in `pickobject/config.py`.

## How To Add a New Place Detector

1. Create a detector class in `placeobject/detectors/`.
2. Subclass `FailureDetector`.
3. Set `failure_type`.
4. Implement `evaluate(self, state)`.
5. Register it in `placeobject/detectors/__init__.py`.
6. Add its name to `ACTIVE_DETECTORS` in `pickobject/config.py` if it is part of condition activation.

## Practical Reading Order for PlaceObject

1. `placeobject/README.md`
2. `placeobject/tree.py`
3. `placeobject/actions/base.py`
4. `placeobject/actions/move_to_place.py`
5. `placeobject/actions/lower_object.py`
6. `placeobject/actions/release_object.py`
7. `placeobject/controller.py`
8. `placeobject/failures.py`
9. `placeobject/detectors/__init__.py`
10. `placeobject/agents/`

## Key Implementation Notes

- place has the controller, BT, failure config, detectors, and wrappers.
- several place conditions are intentionally scaffolded but commented out.
- place shares agent and detector activation config with pick.
- place recovery exists and logs decisions, but place has no standalone CLI/MCP entry file of its own.
