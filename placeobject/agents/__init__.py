"""PlaceObject-specific wrappers over the shared agent implementations.

Naming convention:
- `agents/` contains the shared generic implementations.
- `placeobject/agents/` contains place-task wrappers prefixed with `Place...`.
"""

from __future__ import annotations

from .base import AgentSpec, PlaceObjectAgent
from .place_execution_verification_agent import PlaceExecutionVerificationAgent
from .place_grasp_verification_agent import PlaceGraspVerificationAgent
from .place_instant_state_monitor_agent import PlaceInstantStateMonitorAgent
from .place_pose_verification_agent import PlacePoseVerificationAgent
from .place_recovery_agent import PlaceRecoveryAgent
from .place_scene_perception_agent import PlaceScenePerceptionAgent
from .place_task_execution_agent import PlaceTaskExecutionAgent
from .place_temporal_monitor_agent import PlaceTemporalMonitorAgent

AGENT_CLASSES: tuple[type[PlaceObjectAgent], ...] = (
    PlaceScenePerceptionAgent,
    PlaceGraspVerificationAgent,
    PlacePoseVerificationAgent,
    PlaceExecutionVerificationAgent,
    PlaceTemporalMonitorAgent,
    PlaceInstantStateMonitorAgent,
    PlaceTaskExecutionAgent,
    PlaceRecoveryAgent,
)

AGENT_SPECS: tuple[AgentSpec, ...] = tuple(
    agent_class.spec() for agent_class in AGENT_CLASSES
)


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
    "PlaceExecutionVerificationAgent",
    "PlaceGraspVerificationAgent",
    "PlaceInstantStateMonitorAgent",
    "PlaceObjectAgent",
    "PlacePoseVerificationAgent",
    "PlaceRecoveryAgent",
    "PlaceScenePerceptionAgent",
    "PlaceTaskExecutionAgent",
    "PlaceTemporalMonitorAgent",
    "find_agents_for_condition",
    "find_agents_for_failure",
    "get_agent_specs",
]
