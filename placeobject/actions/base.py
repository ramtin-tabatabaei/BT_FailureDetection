from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import py_trees

_ACTION_DURATION = float(os.environ.get("BT_ACTION_DURATION_SECONDS", "3"))


@dataclass(frozen=True)
class ConditionSpec:
    """Stable descriptor for one condition check in a PlaceObject action."""
    condition_id: str
    question: str
    failure_type: str
    agent_name: str | None = None
    detector_name: str | None = None
    image_source: str = "scene_camera"

    def should_check(self) -> bool:
        from pickobject.config import ACTIVE_AGENTS, ACTIVE_DETECTORS
        agent_ok = bool(self.agent_name) and self.agent_name in ACTIVE_AGENTS
        detector_ok = bool(self.detector_name) and self.detector_name in ACTIVE_DETECTORS
        return agent_ok or detector_ok


def failure_check(
    *,
    condition_id: str,
    question: str,
    failure_type: str,
    agent_name: str | None = None,
    detector_name: str | None = None,
    image_source: str = "scene_camera",
) -> ConditionSpec:
    return ConditionSpec(
        condition_id=condition_id,
        question=question,
        failure_type=failure_type,
        agent_name=agent_name,
        detector_name=detector_name,
        image_source=image_source,
    )


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
            if not cond.should_check():
                continue
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


class TimedPlaceAction(PlaceActionWithConditions):
    """Place action that animates a loading arrow over BT_ACTION_DURATION_SECONDS."""

    action_text: str = ""

    def __init__(self, name: str, controller: Any) -> None:
        super().__init__(name, controller)
        self._start_time: Optional[float] = None

    def initialise(self) -> None:
        self._start_time = None

    def update(self) -> py_trees.common.Status:
        if self._start_time is None:
            status = self._run_conditions("pre", self.preconditions)
            if status != py_trees.common.Status.SUCCESS:
                return status
            self.controller.set_current_step(self.name)
            self._start_time = time.monotonic()
            print(f"\n[Action] {self.action_text}", end="", flush=True)

        elapsed = time.monotonic() - self._start_time
        if elapsed >= _ACTION_DURATION:
            print(f"\r[Action] {self.action_text}  {'—' * 20}> done", flush=True)
            status = self._run_conditions("post", self.postconditions)
            if status != py_trees.common.Status.SUCCESS:
                return status
            self.controller.state["last_valid_bt_step"] = self.name
            self.on_success()
            return py_trees.common.Status.SUCCESS

        fraction = elapsed / _ACTION_DURATION if _ACTION_DURATION > 0 else 1.0
        dashes = int(fraction * 18)
        arrow = "-" * dashes + "->"
        print(f"\r[Action] {self.action_text}  {arrow:<21}", end="", flush=True)
        return py_trees.common.Status.RUNNING

    def on_success(self) -> None:
        """Override for post-success hooks."""
