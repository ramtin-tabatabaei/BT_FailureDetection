# PickObject BT

This repository contains a small behavior tree (BT) package for a `PickObject` task.

It supports two ways of running:

- `manual / human mode`: a human answers `y/n` condition questions in the terminal
- `MCP / scripted mode`: an external agent or script drives the BT through MCP tools

The code does not directly connect to a robot. It is a BT engine plus failure/recovery logic.

## Main Idea

The BT runs a fixed sequence of actions:

1. `ComputeGraspPose`
2. `MoveToPreGrasp`
3. `MoveToGrasp`
4. `CloseGripper`
5. `LiftObject`

Each action can have:

- `preconditions`
- `postconditions`
- `runtime failure hotkeys` during timed actions

At the moment, `hold_conditions` are not used in the action code.

If a condition fails, the BT maps that failed check to a failure type such as:

- `object_not_found`
- `execution_mismatch`
- `grip_loss`

Then the system looks up the configured recovery options for that failure and asks the user or external agent to choose one.

## Repository Layout

- [main.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/main.py): entry points for manual mode and MCP mode
- [controller.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/controller.py): BT state, ticking, failure handling, recovery selection
- [tree.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/tree.py): action sequence definition
- [actions/](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/actions): action nodes and condition checks
- [agents/](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/agents): failure agents used in scripted/MCP mode
- [failures.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/failures.py): failure registry and runtime/hotkey rules
- [configs/PickObject_failures_fixed.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_failures_fixed.json): failure definitions, retry budgets, recoveries
- [configs/PickObject_scene.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_scene.json): scene and diagnosis prompt config
- [providers.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/providers.py): terminal and scripted providers

## Install Notes

At minimum, manual mode needs `py_trees`.

MCP mode also needs the `mcp` package because [main.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/main.py) imports `FastMCP`.

## Run Manual Mode

Run from the parent directory of the package:

```bash
cd "/Users/stabatabaeim/Univerisity/Year 3/BT Study/Codes"
python3 -m pickobject
```

Manual mode behavior:

- `preconditions`: ask the human `y/n`
- `postconditions`: ask the human `y/n`
- timed actions: show hotkeys for runtime failures
- repeated identical `pre` and `post` checks in the same tick are reused

Useful environment variables:

```bash
BT_ACTION_DURATION_SECONDS=5
BT_TICK_PERIOD_SECONDS=2
BT_MAX_TICKS=100
```

Example:

```bash
BT_ACTION_DURATION_SECONDS=0 BT_TICK_PERIOD_SECONDS=0 python3 -m pickobject
```

## Run MCP Mode

Run:

```bash
cd "/Users/stabatabaeim/Univerisity/Year 3/BT Study/Codes"
python3 -m pickobject --mcp
```

In MCP mode, the package uses the scripted controller, not the terminal one.

Important:

- the BT does not inspect the world by itself
- an external agent must set condition answers and choose recoveries through MCP tools

Typical MCP flow:

1. `reset_state()`
2. `get_condition_ids()`
3. external agent decides what is true
4. `set_condition(...)` or `set_conditions(...)`
5. `tick_once()`
6. if there is a failure, call `get_recovery_options()`
7. choose one recovery
8. `apply_recovery_choice(...)`
9. `tick_once()` again

## Manual Mode vs MCP Mode

### Manual / Human Mode

- Uses `TerminalConditionProvider`
- Uses `TerminalChoiceProvider`
- Human answers questions in the terminal
- During timed actions, failures are injected with hotkeys

### MCP / Scripted Mode

- Uses `ScriptedConditionProvider`
- Uses `ScriptedChoiceProvider`
- External agent/script sets condition results
- External agent/script chooses recoveries
- Failure agents can be triggered with `set_failure_agent_input(...)`

## Failure and Recovery Model

Failures are defined in [configs/PickObject_failures_fixed.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_failures_fixed.json).

Each failure has:

- `retry_budget`
- `recoveries`

Example:

```json
"grip_loss": {
  "retry_budget": 2,
  "recoveries": [
    "stop_motion_immediately",
    "search_for_dropped_object",
    "re_approach_and_regrasp",
    "return_to_pre_transport_state",
    "ask_user"
  ]
}
```

When a failure happens:

1. the BT stores `last_failure`
2. the recovery options are read from config
3. one recovery is chosen
4. retry count is incremented
5. the tree resumes from the failed step by default

If the retry budget is exhausted, the run stops.

## Recovery Resume Behavior

By default, after a recovery is chosen, the BT resumes from the failed step.

If you want a specific recovery to jump to a different step, define metadata in the optional top-level `recoveries` section of [configs/PickObject_failures_fixed.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_failures_fixed.json).

Example:

```json
{
  "PickObject": {
    "failures": {
      "execution_mismatch": {
        "retry_budget": 2,
        "recoveries": [
          "replace_with_valid_action",
          "reorder_actions"
        ]
      }
    },
    "recoveries": {
      "replace_with_valid_action": {
        "restart_step": "MoveToPreGrasp"
      },
      "reorder_actions": {
        "restart_step": "ComputeGraspPose"
      }
    }
  }
}
```

Supported keys:

- `restart_step`
- `resume_step`

If no step is configured, the controller resumes from the failure step.

## How To Add a New Failure

There are two common cases.

### Case 1: Condition-Based Failure

Use this when a failure is simply the result of a condition returning `False`.

Steps:

1. Add the failure to [configs/PickObject_failures_fixed.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_failures_fixed.json)
2. Reference it from an action condition with `failure_check(...)`

Example config:

```json
"slippage": {
  "retry_budget": 2,
  "recoveries": [
    "stop_motion_immediately",
    "regrasp",
    "ask_user"
  ]
}
```

Example action usage:

```python
failure_check(
    condition_id="ObjectStable",
    question="Is the object stable in the gripper?",
    failure_type="slippage",
)
```

This is enough for manual mode and scripted condition failures.

### Case 2: Runtime / Agent-Detected Failure

Use this when the failure should be actively monitored or injected by an external agent.

Steps:

1. Add the failure to [configs/PickObject_failures_fixed.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_failures_fixed.json)
2. Add it to [failures.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/failures.py)
3. Create an agent file in [agents/](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/agents)
4. Register the agent in [agents/__init__.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/agents/__init__.py)

Example in `failures.py`:

```python
"slippage": {"monitor_during_actions": True, "hotkey": "s"}
```

Example agent:

```python
from .base import FailureAgent, FailureSignal

class SlippageAgent(FailureAgent):
    failure_type = "slippage"

    def evaluate(self, state):
        if not self._is_triggered(state):
            return None
        return FailureSignal(self.failure_type, detected=True, details=self._input(state))
```

Then register it in [agents/__init__.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/agents/__init__.py).

## How To Add a Recovery

If you only need a named recovery option:

1. Add the recovery name inside the failure’s `recoveries` list in [configs/PickObject_failures_fixed.json](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/configs/PickObject_failures_fixed.json)

Example:

```json
"execution_mismatch": {
  "retry_budget": 2,
  "recoveries": [
    "replace_with_valid_action",
    "reorder_actions",
    "re_evaluate_current_state"
  ]
}
```

If you also want recovery metadata such as where to resume:

1. Add a top-level `recoveries` section
2. Add an entry for that recovery name

Example:

```json
"recoveries": {
  "re_evaluate_current_state": {
    "restart_step": "MoveToPreGrasp"
  }
}
```

At the moment, recoveries are names plus optional resume metadata. They are not separate executable BT actions yet.

## How Conditions Work

A condition is defined by:

- `condition_id`: stable key for the check
- `question`: human-readable prompt
- `failure_type`: what failure to report if the answer is `False`

Example:

```python
failure_check(
    condition_id="TargetVisible",
    question="Can the robot currently see the target object?",
    failure_type="object_not_found",
)
```

`condition_id` is important because:

- manual mode shows it in the terminal
- MCP mode uses it as the key for `set_condition(...)`
- tick logs record it

## How Runtime Failures Work

Timed actions show hotkeys such as:

- `x=exec_mismatch`
- `f=freezing`
- `g=grip_loss`
- `c=collision`
- `l=force_limit`
- `t=action_timeout`

Those mappings come from [failures.py](/Users/stabatabaeim/Univerisity/Year%203/BT%20Study/Codes/pickobject/failures.py).

In manual mode, press those keys during a timed action to inject a runtime failure.

## Notes About Hold Conditions

The project currently treats hold monitoring through runtime hotkeys or scripted failure input.

In the current action files:

- `hold_conditions` are empty
- manual mode does not use hold questions

If you want to reintroduce `hold_conditions` later for scripted/MCP mode, you can, but keep the interaction model clear:

- human mode: avoid blocking prompts during motion
- scripted mode: external agent can update conditions or inject failures while the action is running

## Recommended Workflow For Changes

When adding or changing task logic:

1. update the failure config
2. update the action condition mapping
3. update `failures.py` if runtime monitoring is needed
4. add/register an agent if scripted runtime detection is needed
5. test in manual mode with `python3 -m pickobject`

## Current Limitations

- recoveries are selected and recorded, but most do not execute different robot-specific behavior yet
- the package does not directly connect to sensors, planners, or hardware
- MCP mode depends on an external agent to provide observations and choices
