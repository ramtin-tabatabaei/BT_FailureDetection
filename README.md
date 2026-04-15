# BT Study — Multi-Agent Robotic Pick-and-Place

A research framework for studying how AI agents interact with **Behaviour Trees (BTs)** in robotic manipulation tasks. The system models a full pick-and-place pipeline with realistic failure modes, multi-agent coordination, and structured recovery decision logging.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     8-Agent System                               │
│                                                                  │
│  ── Perception / Monitoring Agents ──────────────────────────── │
│                                                                  │
│  ScenePerceptionAgent      VLM                                   │
│    detects: object_not_found                                     │
│    when:    before any movement (scene overview camera)          │
│                                                                  │
│  GraspVerificationAgent    VLM                                   │
│    detects: wrong_object_selection                               │
│    when:    gripper positioned, before closing (wrist camera)    │
│                                                                  │
│  PoseVerificationAgent     cheap model → VLM                     │
│    detects: wrong_position, wrong_orientation                    │
│    when:    after each movement                                   │
│                                                                  │
│  ExecutionVerificationAgent  cheap model → VLM                   │
│    detects: execution_mismatch                                   │
│    when:    pre/post conditions of any action                    │
│                                                                  │
│  TemporalMonitorAgent      cheap sensor → VLM (image sequence)   │
│    detects: freezing, action_timeout                             │
│    when:    continuously during action execution                  │
│                                                                  │
│  InstantStateMonitorAgent  cheap sensor → VLM (single frame)     │
│    detects: grip_loss, collision, force_limit_exceeded           │
│    when:    continuously during action execution                  │
│                                                                  │
│  ── LLM Task Agents (MCP Server) ────────────────────────────── │
│                                                                  │
│  TaskExecutionAgent        task_* tools                          │
│    drives BT tick loop, manages pick → place → done transitions  │
│                                                                  │
│  RecoveryAgent             recovery_* tools                      │
│    called on failure; reasons about and applies recovery         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Important: FailureDetectors are NOT agents

`pickobject/detectors/` contains 10 rule-based **FailureDetector** classes. These are **not agents** — they are simple relay components:

```python
# All they do:
def evaluate(self, state):
    if state["agent_inputs"]["grip_loss"]["detected"]:   # flag set by InstantStateMonitorAgent
        return FailureSignal(...)
```

A perception/monitoring agent sets the flag → the FailureDetector forwards it to the BT. No reasoning, no decisions. The name *detector* reflects this.

| Class | Set by |
|---|---|
| `ObjectNotFoundDetector` | `ScenePerceptionAgent` |
| `WrongObjectSelectionDetector` | `GraspVerificationAgent` |
| `WrongPositionDetector` | `PoseVerificationAgent` |
| `WrongOrientationDetector` | `PoseVerificationAgent` |
| `ExecutionMismatchDetector` | `ExecutionVerificationAgent` |
| `FreezingDetector` | `TemporalMonitorAgent` |
| `ActionTimeoutDetector` | `TemporalMonitorAgent` |
| `GripLossDetector` | `InstantStateMonitorAgent` |
| `CollisionDetector` | `InstantStateMonitorAgent` |
| `ForceLimitExceededDetector` | `InstantStateMonitorAgent` (sensor only, no VLM) |

---

## Behaviour Trees

### PickObject BT
```
PickObject Sequence {→}
  ├── ComputeGraspPose     pre: TargetVisible
  ├── MoveToPreGrasp       pre: GraspPoseValid
  ├── MoveToGrasp          pre: PreGraspPoseConfirmed, GripperReadyBeforeGrasp
  ├── CloseGripper         pre: AtGraspPose, GripperReadyToClose
  └── LiftObject           pre: ObjectInGripper
```

### PlaceObject BT
```
PlaceObject Sequence {→}
  ├── MoveToPlace          pre: ObjectSecuredInGripper, PlaceLocationVisible
  │                        post: AtPlaceLocation
  ├── LowerObject          pre: AtPlaceLocation
  │                        post: ObjectAtPlaceHeight
  └── ReleaseObject        pre: ObjectAtPlaceHeight
                           post: PlacementConfirmed  →  place_succeeded = True
```

---

## Project Structure

```
Codes/
├── pickobject/
│   ├── actions/            BT action nodes (ComputeGraspPose, MoveToGrasp, ...)
│   ├── detectors/          Rule-based failure signal relays (NOT agents)
│   ├── controller.py       PickObjectController — BT state + tick infrastructure
│   ├── failure_manager.py  FailureDetectorManager — iterates detectors each tick
│   ├── providers.py        Condition providers (scripted for MCP, terminal for demo)
│   ├── tree.py             Builds the PickObject BT
│   └── main.py             Legacy single-agent MCP server (use multi_agent_server.py)
│
├── placeobject/
│   ├── actions/            BT action nodes (MoveToPlace, LowerObject, ReleaseObject)
│   ├── controller.py       PlaceObjectController
│   └── tree.py             Builds the PlaceObject BT
│
├── orchestrator.py         PickAndPlaceOrchestrator — phase management + combined log
├── multi_agent_server.py   Unified MCP server (task_* / recovery_* / pick_* / place_*)
├── visualize_trees.py      Interactive matplotlib BT visualizer
└── TestBTCode.py           Simple prototype BT (not part of multi-agent system)
```

---

## MCP Tool Groups

### `task_*` — TaskExecutionAgent
| Tool | Description |
|---|---|
| `task_get_summary` | Overall task status (phase, ticks, successes, failures) |
| `task_tick_current` | Advance active BT by one tick |
| `task_advance_phase` | Manually move pick → place |
| `task_abort(reason)` | Mark task as failed |
| `task_reset_all` | Reset both BTs to initial state |
| `task_get_combined_log` | Merged tick-history across both BTs |
| `task_describe_architecture` | Full agent architecture summary |

### `recovery_*` — RecoveryAgent
| Tool | Description |
|---|---|
| `recovery_get_context(phase, failure_type)` | Available recoveries, retry budget, recent history |
| `recovery_apply(phase, failure_type, chosen_recovery, reasoning)` | Apply decision + log reasoning |
| `recovery_get_history` | All recovery decisions made this session |

### `pick_*` — PickObject BT tools
| Tool | Description |
|---|---|
| `pick_describe_tree` | Unicode diagram of PickObject BT |
| `pick_get_condition_ids` | All condition IDs with questions and failure types |
| `pick_set_condition(id, value)` | Override a single condition |
| `pick_set_conditions({...})` | Override multiple conditions at once |
| `pick_set_failure(type, detected)` | Inject a failure signal from a perception agent |
| `pick_get_state` | Current world-state snapshot |
| `pick_get_tick_history` | Full per-tick log |
| `pick_reset` | Reset to initial state |

### `place_*` — PlaceObject BT tools
Same structure as `pick_*` but for the PlaceObject phase.

---

## Typical Experiment Loop

```
1. task_get_summary              → check we are in "pick" phase
2. pick_describe_tree            → understand BT structure
3. pick_get_condition_ids        → see all condition IDs
4. pick_set_conditions({...})    → inject a failure scenario
                                   e.g. {"TargetVisible": false}

5. loop:
     task_tick_current
       → tree_status == FAILURE?
           recovery_get_context("pick", last_failure)
           recovery_apply("pick", failure, chosen, reasoning)
       → tree_status == SUCCESS / phase becomes "place"?
           break

6. task_advance_phase            → move to place phase
7. place_describe_tree
8. place_set_conditions({...})   → inject place scenario
9. loop: task_tick_current       → drive place BT

10. task_get_combined_log        → full cross-agent experiment record
```

---

## Running the System

### Interactive demo (terminal y/n prompts)
```bash
python -m pickobject
```

### MCP server (multi-agent, for Claude / LLM agents)
```bash
pip install mcp
python multi_agent_server.py
```

### BT visualizer
```bash
python3 visualize_trees.py
# Opens three interactive windows (zoom/pan toolbar)
# Saves: bt_trees.png (combined), bt_placeobject.png (standalone)
```

---

## Failure Types

| Failure | Detector | Detected by |
|---|---|---|
| `object_not_found` | `ObjectNotFoundDetector` | ScenePerceptionAgent (VLM) |
| `wrong_object_selection` | `WrongObjectSelectionDetector` | GraspVerificationAgent (VLM) |
| `wrong_position` | `WrongPositionDetector` | PoseVerificationAgent (cheap → VLM) |
| `wrong_orientation` | `WrongOrientationDetector` | PoseVerificationAgent (cheap → VLM) |
| `execution_mismatch` | `ExecutionMismatchDetector` | ExecutionVerificationAgent (cheap → VLM) |
| `freezing` | `FreezingDetector` | TemporalMonitorAgent (velocity → image sequence) |
| `action_timeout` | `ActionTimeoutDetector` | TemporalMonitorAgent (timer → image sequence) |
| `grip_loss` | `GripLossDetector` | InstantStateMonitorAgent (force → single frame) |
| `collision` | `CollisionDetector` | InstantStateMonitorAgent (force/torque → single frame) |
| `force_limit_exceeded` | `ForceLimitExceededDetector` | InstantStateMonitorAgent (force sensor only) |
