from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

import py_trees


@dataclass(frozen=True)
class ConditionSpec:
    """Stable descriptor for one condition check in a PlaceObject action."""
    condition_id: str
    question: str
    failure_type: str


def failure_check(*, condition_id: str, question: str, failure_type: str) -> ConditionSpec:
    return ConditionSpec(condition_id=condition_id, question=question, failure_type=failure_type)


class PlaceAction(py_trees.behaviour.Behaviour):
    """Base node that holds a reference to the PlaceObjectController."""

    def __init__(self, name: str, controller: Any) -> None:
        super().__init__(name)
        self.controller = controller


class PlaceActionWithConditions(PlaceAction):
    """Adds pre/postcondition phases to a PlaceAction.

    Subclasses declare ``preconditions`` and ``postconditions`` as class-level
    tuples of :class:`ConditionSpec`.  The ``_run_conditions`` helper iterates
    them and asks the controller to evaluate each one; the first failure triggers
    the associated failure type on the controller and returns FAILURE.
    """

    preconditions: Tuple[ConditionSpec, ...] = ()
    postconditions: Tuple[ConditionSpec, ...] = ()

    def _run_conditions(
        self, phase: str, conditions: Tuple[ConditionSpec, ...]
    ) -> py_trees.common.Status:
        for cond in conditions:
            self.controller.set_current_step(self.name)
            self.controller.set_current_condition(cond.condition_id, phase, cond.question)
            result = self.controller.check(cond.condition_id, cond.question)
            if not result:
                self.controller.detect_failure([cond.failure_type], fallback=cond.failure_type)
                self.controller.set_current_condition(None, None)
                return py_trees.common.Status.FAILURE
        self.controller.set_current_condition(None, None)
        return py_trees.common.Status.SUCCESS


class InstantPlaceAction(PlaceActionWithConditions):
    """Action that completes in a single tick: runs pre → perform → post."""

    def update(self) -> py_trees.common.Status:
        status = self._run_conditions("pre", self.preconditions)
        if status != py_trees.common.Status.SUCCESS:
            return status

        self.controller.set_current_step(self.name)
        self.perform_action()

        status = self._run_conditions("post", self.postconditions)
        if status != py_trees.common.Status.SUCCESS:
            return status

        self.controller.state["last_valid_bt_step"] = self.name
        self.on_success()
        return py_trees.common.Status.SUCCESS

    def perform_action(self) -> None:
        """Override to add side-effects (e.g. set world-state flags)."""

    def on_success(self) -> None:
        """Override for post-success hooks."""
