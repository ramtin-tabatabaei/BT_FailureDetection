from .action_timeout_agent import ActionTimeoutAgent
from .collision_agent import CollisionAgent
from .execution_mismatch_agent import ExecutionMismatchAgent
from .force_limit_exceeded_agent import ForceLimitExceededAgent
from .freezing_agent import FreezingAgent
from .grip_loss_agent import GripLossAgent
from .object_not_found_agent import ObjectNotFoundAgent
from .wrong_object_selection_agent import WrongObjectSelectionAgent
from .wrong_orientation_agent import WrongOrientationAgent
from .wrong_position_agent import WrongPositionAgent

AGENT_CLASSES = (
    ActionTimeoutAgent,
    CollisionAgent,
    ExecutionMismatchAgent,
    ForceLimitExceededAgent,
    FreezingAgent,
    GripLossAgent,
    ObjectNotFoundAgent,
    WrongObjectSelectionAgent,
    WrongOrientationAgent,
    WrongPositionAgent,
)

FAILURE_AGENT_CLASSES = {
    agent_class.failure_type: agent_class
    for agent_class in AGENT_CLASSES
}

__all__ = [
    "ActionTimeoutAgent",
    "CollisionAgent",
    "ExecutionMismatchAgent",
    "FAILURE_AGENT_CLASSES",
    "ForceLimitExceededAgent",
    "FreezingAgent",
    "GripLossAgent",
    "ObjectNotFoundAgent",
    "WrongObjectSelectionAgent",
    "WrongOrientationAgent",
    "WrongPositionAgent",
]
