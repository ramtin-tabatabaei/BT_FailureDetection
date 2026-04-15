from __future__ import annotations

import py_trees

from .actions import (
    CloseGripper,
    ComputeGraspPose,
    LiftObject,
    MoveToGrasp,
    MoveToPreGrasp,
)

# Edit this list to change the PickObject flow.
PICK_SEQUENCE = [
    "ComputeGraspPose",
    "MoveToPreGrasp",
    "MoveToGrasp",
    "CloseGripper",
    "LiftObject",
]


def build_step(step_name: str, controller) -> py_trees.behaviour.Behaviour:
    factories = {
        "ComputeGraspPose": lambda: ComputeGraspPose("ComputeGraspPose", controller),
        "MoveToPreGrasp": lambda: MoveToPreGrasp("MoveToPreGrasp", controller),
        "MoveToGrasp": lambda: MoveToGrasp("MoveToGrasp", controller),
        "CloseGripper": lambda: CloseGripper("CloseGripper", controller),
        "LiftObject": lambda: LiftObject("LiftObject", controller),
    }
    if step_name not in factories:
        raise KeyError(f"Unknown action step '{step_name}'")
    return factories[step_name]()


def build_sequence(name: str, controller, step_names: list[str], memory: bool = True) -> py_trees.behaviour.Behaviour:
    seq = py_trees.composites.Sequence(name, memory=memory)
    seq.add_children([build_step(step_name, controller) for step_name in step_names])
    return seq


def make_pick_object_tree(controller) -> py_trees.behaviour.Behaviour:
    return build_sequence("PickObject", controller, PICK_SEQUENCE)
