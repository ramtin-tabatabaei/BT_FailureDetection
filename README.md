# BT Study - Multi-Agent Pick-and-Place

This repository is a behaviour-tree study project for a robotic pick-and-place task.

The real execution backbone is:

1. `pickobject` builds and runs the pick BT.
2. `placeobject` builds and runs the place BT.
3. `orchestrator.py` switches between pick and place phases.
4. `multi_agent_server.py` exposes MCP tools for task execution, recovery, and both BTs.
5. `agents/` contains shared agent implementations or helper classes.

The codebase is split into two kinds of components:

- BT infrastructure: controllers, trees, actions, failure managers, configs.
- Agent-facing infrastructure: shared agents, task-specific wrappers, MCP tools.

## End-to-End Connection Flow

The main connection path is:

1. An action in `pickobject/actions/` or `placeobject/actions/` declares a condition with `failure_check(...)`.
2. That condition names a `condition_id`, `failure_type`, `agent_name`, and optionally a `detector_name`.
3. The controller evaluates that condition through a provider.
4. If the condition fails, the controller marks the corresponding `failure_type`.
5. For external runtime signals, an agent injects data into `state["agent_inputs"]`.
6. A detector in `pickobject/detectors/` or `placeobject/detectors/` relays that injected signal into the BT as a `FailureSignal`.
7. The failure manager chooses the first triggered detector.
8. The controller records the failure and exposes recovery options.
9. The RecoveryAgent or MCP recovery tool applies a configured recovery.
10. The orchestrator advances from `pick` to `place` when `pick_succeeded` becomes true, then to `done` when `place_succeeded` becomes true.

## How Agents, Detectors, and Failures Are Turned On or Off

There are three different switches in this repository.

### 1. Turn a condition check on or off

Pick and place condition checks are gated by `ConditionSpec.should_check()`.

For pick:
- `pickobject/actions/base.py` checks `pickobject/config.py`
- `ACTIVE_AGENTS`
- `ACTIVE_DETECTORS`

For place:
- `placeobject/actions/base.py` also imports the same `pickobject/config.py`
- this means place currently reuses the pick config toggles

If the `agent_name` and `detector_name` for a condition are both inactive, that condition is skipped.

To turn an agent on:

```python
ACTIVE_AGENTS = {
    "ScenePerceptionAgent",
    "PoseVerificationAgent",
}
```

To turn it off, remove its name from `ACTIVE_AGENTS`.

To turn a detector on:

```python
ACTIVE_DETECTORS = {
    "ObjectNotFoundDetector",
    "WrongPositionDetector",
}
```

To turn it off, remove its name from `ACTIVE_DETECTORS`.

### 2. Turn a failure type on or off

Failure managers use selectors:

- `pickobject/experiment.py`
- `placeobject/experiment.py`

Both selectors enable every configured failure by default. If you want to disable a failure type for an experiment, remove it from the selector's `enabled_failures` set or provide a customized selector to the failure manager.

This is different from `ACTIVE_DETECTORS`.

- `ACTIVE_DETECTORS` affects whether a condition check is allowed to run.
- `enabled_failures` affects whether the failure manager will accept a detector result for that failure type.

### 3. Turn runtime monitoring on or off

Pick runtime monitoring uses:

- `pickobject/failures.py`
- `RUNTIME_FAILURE_TYPES`
- `TimedInterruptibleAction.update()` in `pickobject/actions/base.py`

If a failure type is marked with `"monitor_during_actions": True`, the pick BT polls it during timed actions.

Place has failure and detector scaffolding for runtime-like failures, but `placeobject/actions/base.py` does not currently poll `poll_runtime_failure()` during timed actions. That means place is not yet wired as deeply as pick for runtime monitoring.

## How To Add a New Failure

The exact steps differ slightly between pick and place.

### Add a new pick failure

1. Add the failure entry to `pickobject/configs/PickObject_failures_fixed.json`.
2. If it is a runtime or hotkey-driven failure, also register it in `pickobject/failures.py`.
3. Create a detector file in `pickobject/detectors/` if the failure is supposed to come from `state["agent_inputs"]`.
4. Register that detector in `pickobject/detectors/__init__.py`.
5. Attach the failure to a BT condition in one of the pick action files with `failure_check(...)`, or inject it through `pick_set_failure(...)`.
6. If it needs a new agent owner, add or update the relevant agent wrapper in `pickobject/agents/`.

Example condition-based failure:

```python
failure_check(
    condition_id="ObjectStable",
    question="Is the object still stable?",
    failure_type="grip_loss",
    agent_name="InstantStateMonitorAgent",
    detector_name="GripLossDetector",
)
```

### Add a new place failure

1. Add the failure entry to `placeobject/failures.py` inside both `FAILURE_RULES` and `FAILURE_CONFIG` if needed.
2. Create a detector file in `placeobject/detectors/` if the failure comes from injected agent input.
3. Register that detector in `placeobject/detectors/__init__.py`.
4. Add or uncomment a `failure_check(...)` in `placeobject/actions/`.
5. If the new failure belongs to a specific high-level agent, add or update a wrapper in `placeobject/agents/`.

## How To Add a New Agent

There are two layers of agents in this repo.

- Shared agent implementations live in `agents/`
- Task-specific wrappers live in `pickobject/agents/` and `placeobject/agents/`

Typical steps:

1. Create or update the shared implementation in `agents/` if the logic should be reusable.
2. Create a task wrapper in `pickobject/agents/` or `placeobject/agents/`.
3. Set these class attributes on the wrapper:
   - `name`
   - `modality`
   - `description`
   - `failure_types`
   - `condition_ids`
4. Register the wrapper in that package's `__init__.py` by adding it to `AGENT_CLASSES`.
5. Reference the agent from an action condition with `agent_name="YourAgentName"`.
6. Add the name to `ACTIVE_AGENTS` in `pickobject/config.py` if you want the conditions to execute.

If you skip step 4, the BT can still use the string name in condition checks, but helper tools such as `find_agents_for_condition()` and `find_agents_for_failure()` will not know about the agent.

## How To Add a New Detector

1. Create a new detector class that subclasses `FailureDetector`.
2. Set its `failure_type`.
3. Implement `evaluate(self, state)` so it returns a `FailureSignal` when the injected input is active.
4. Register it in the task's `detectors/__init__.py`.
5. Reference it from a condition with `detector_name="YourDetectorName"` if it is part of a BT condition path.
6. Add the detector name to `ACTIVE_DETECTORS` if you want condition-level checks to run.

Minimal detector example:

```python
class MyFailureDetector(FailureDetector):
    failure_type = "my_failure"

    def evaluate(self, state):
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
```

## Repository Map

### Top-level files

- `README.md`: repository-level architecture and extension guide.
- `multi_agent_server.py`: MCP server for task, recovery, pick, and place tools.
- `orchestrator.py`: phase-level coordinator between pick and place controllers.
- `run_pick.py`: small runner that calls the real ScenePerceptionAgent and scripts everything else.
- `run_multiagent.py`: script-style end-to-end runner using the orchestrator and task wrappers.
- `visualize_trees.py`: matplotlib visualizer for the BTs.
- `generate_demo_images.py`: creates schematic demo images for condition checks.
- `inspect_pickobject_code.py`: helper script that uses `TaskCodeReaderAgent` to summarize the pick code.
- `test.py`: standalone experimental script for agent logic.
- `api_key.txt`: optional Anthropic API key file used by VLM-style shared agents.
- `robot_detected.jpg`: sample scene image.

### Shared `agents/` directory

- `agents/__init__.py`: lazy exports for shared agent modules.
- `agents/base.py`: shared dataclasses such as `ConditionVerification`, `RecoveryDecision`, and decision payloads.
- `agents/scene_perception_agent.py`: real VLM scene checker with `predict()` fallback.
- `agents/grasp_verification_agent.py`: real VLM wrist-camera checker with `predict()` fallback.
- `agents/execution_verification_agent.py`: real VLM transition checker plus demo prediction helpers.
- `agents/pose_verification_agent.py`: demo-facing pose result wrapper.
- `agents/instant_state_monitor_agent.py`: demo-facing instant monitor result wrapper.
- `agents/temporal_monitor_agent.py`: demo-facing temporal monitor result wrapper.
- `agents/task_execution_agent.py`: wrapper around `PickAndPlaceOrchestrator`.
- `agents/recovery_agent.py`: simple recovery-policy helper.
- `agents/task_code_reader_agent.py`: development helper that parses pick BT files and reports action-agent wiring.

### `pickobject/`

This is the more complete task package.

- `pickobject/__init__.py`: exports the pick MCP entry points.
- `pickobject/__main__.py`: allows `python -m pickobject`.
- `pickobject/main.py`: standalone pick MCP server and interactive terminal runner.
- `pickobject/config.py`: loads config JSON, scene config, camera mapping, target labels, and the active agent/detector toggles.
- `pickobject/controller.py`: main pick controller, state store, tick logging, recovery handling, and controller factories.
- `pickobject/tree.py`: builds the pick sequence from `PICK_SEQUENCE`.
- `pickobject/providers.py`: terminal and scripted providers, plus keyboard failure monitor.
- `pickobject/failures.py`: runtime failure metadata and terminal hotkey mapping.
- `pickobject/failure_manager.py`: detector registry and failure detection loop.
- `pickobject/experiment.py`: pick failure selector.
- `pickobject/configs/PickObject_failures_fixed.json`: retry budgets and recoveries.
- `pickobject/configs/PickObject_scene.json`: scene and diagnosis metadata.
- `pickobject/actions/`: pick BT nodes.
- `pickobject/agents/`: pick-specific wrappers over shared agents.
- `pickobject/detectors/`: pick-specific detector relay classes.
- `pickobject/README.md`: pick package documentation.

### `placeobject/`

This is the place task package.

- `placeobject/__init__.py`: exports the place controller factory.
- `placeobject/controller.py`: place controller, state store, logging, and recovery support.
- `placeobject/tree.py`: builds the place sequence.
- `placeobject/failures.py`: place failure rules and recovery config.
- `placeobject/failure_manager.py`: place detector registry and failure detection loop.
- `placeobject/experiment.py`: place failure selector.
- `placeobject/actions/`: place BT nodes.
- `placeobject/agents/`: place-specific wrappers over shared agents.
- `placeobject/detectors/`: place-specific detector relay classes.
- `placeobject/README.md`: place package documentation.

## PickObject File Connections

The most important pick chain is:

`pickobject/tree.py`
-> instantiates action classes from `pickobject/actions/`
-> each action uses `ConditionSpec` from `pickobject/actions/base.py`
-> each condition names a `failure_type`, `agent_name`, and `detector_name`
-> `pickobject/controller.py` evaluates the condition via a provider
-> `pickobject/failure_manager.py` checks `pickobject/detectors/`
-> recovery options come from `pickobject/configs/PickObject_failures_fixed.json`

## PlaceObject File Connections

The most important place chain is:

`placeobject/tree.py`
-> instantiates action classes from `placeobject/actions/`
-> `placeobject/actions/base.py` evaluates enabled conditions
-> `placeobject/controller.py` records state, failures, and recovery
-> `placeobject/failure_manager.py` checks `placeobject/detectors/`
-> recovery options come from `placeobject/failures.py`

Important current status:

- most place action condition blocks are present but commented out
- because of that, `placeobject` is structurally ready but less wired than `pickobject`

## MCP Tool Groups

`multi_agent_server.py` exposes four tool groups:

- `task_*`: overall task summary, ticking, reset, abort, combined history.
- `recovery_*`: recovery context, apply recovery, recovery history.
- `pick_*`: inspect and drive the pick BT.
- `place_*`: inspect and drive the place BT.

## Recommended Reading Order

If someone is new to the codebase, read in this order:

1. `README.md`
2. `multi_agent_server.py`
3. `orchestrator.py`
4. `pickobject/README.md`
5. `pickobject/tree.py`
6. `pickobject/actions/`
7. `pickobject/controller.py`
8. `placeobject/README.md`
9. `placeobject/tree.py`
10. `placeobject/actions/`

## Current Implementation Notes

- `pickobject` is the stronger reference implementation.
- `placeobject` has the controller, agents, detectors, and recovery structure, but several action-level condition checks are still commented out.
- both pick and place currently use `pickobject/config.py` for `ACTIVE_AGENTS` and `ACTIVE_DETECTORS`.
- shared VLM-style agents look for `api_key.txt` or `ANTHROPIC_API_KEY`.
