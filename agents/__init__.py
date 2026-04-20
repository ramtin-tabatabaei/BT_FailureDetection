from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "ExecutionVerificationAgent": ".execution_verification_agent",
    "GraspVerificationAgent": ".grasp_verification_agent",
    "InstantStateMonitorAgent": ".instant_state_monitor_agent",
    "PoseVerificationAgent": ".pose_verification_agent",
    "RecoveryAgent": ".recovery_agent",
    "ScenePerceptionAgent": ".scene_perception_agent",
    "TaskCodeReaderAgent": ".task_code_reader_agent",
    "TaskExecutionAgent": ".task_execution_agent",
    "TemporalMonitorAgent": ".temporal_monitor_agent",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_EXPORTS[name], __name__)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(globals().keys() | set(__all__))
