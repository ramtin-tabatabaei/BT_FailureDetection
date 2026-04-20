"""PickObject-specific wrappers over the shared agent implementations.

Naming convention:
- `agents/` contains the shared generic implementations.
- `pickobject/agents/` contains pick-task wrappers prefixed with `Pick...`.
"""

from __future__ import annotations

from .base import AgentSpec, PickObjectAgent
from .pick_execution_verification_agent import PickExecutionVerificationAgent
from .pick_grasp_verification_agent import PickGraspVerificationAgent
from .pick_instant_state_monitor_agent import PickInstantStateMonitorAgent
from .pick_pose_verification_agent import PickPoseVerificationAgent
from .pick_recovery_agent import PickRecoveryAgent
from .pick_scene_perception_agent import PickScenePerceptionAgent
from .pick_task_execution_agent import PickTaskExecutionAgent
from .pick_temporal_monitor_agent import PickTemporalMonitorAgent

AGENT_CLASSES: tuple[type[PickObjectAgent], ...] = (
    PickScenePerceptionAgent,
    PickGraspVerificationAgent,
    PickPoseVerificationAgent,
    PickExecutionVerificationAgent,
    PickTemporalMonitorAgent,
    PickInstantStateMonitorAgent,
    PickTaskExecutionAgent,
    PickRecoveryAgent,
)

AGENT_SPECS: tuple[AgentSpec, ...] = tuple(agent_class.spec() for agent_class in AGENT_CLASSES)


def get_agent_specs() -> list[dict[str, object]]:
    return [spec.to_dict() for spec in AGENT_SPECS]


def find_agents_for_failure(failure_type: str) -> list[dict[str, object]]:
    return [
        spec.to_dict()
        for spec in AGENT_SPECS
        if failure_type in spec.failure_types
    ]


def find_agents_for_condition(condition_id: str) -> list[dict[str, object]]:
    return [
        spec.to_dict()
        for spec in AGENT_SPECS
        if condition_id in spec.condition_ids
    ]


__all__ = [
    "AGENT_CLASSES",
    "AGENT_SPECS",
    "AgentSpec",
    "PickExecutionVerificationAgent",
    "PickGraspVerificationAgent",
    "PickInstantStateMonitorAgent",
    "PickObjectAgent",
    "PickPoseVerificationAgent",
    "PickRecoveryAgent",
    "PickScenePerceptionAgent",
    "PickTaskExecutionAgent",
    "PickTemporalMonitorAgent",
    "find_agents_for_condition",
    "find_agents_for_failure",
    "get_agent_specs",
]
