from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

import py_trees

from ..config import ACTION_DURATION_SECONDS, ACTION_HOTKEY_HINT
from ..failures import RUNTIME_FAILURE_TYPES


class PickAction(py_trees.behaviour.Behaviour):
    def __init__(self, name: str, controller: Any):
        super().__init__(name)
        self.controller = controller


@dataclass(frozen=True)
class ConditionSpec:
    # condition_id is the stable check label; question is the prompt used to evaluate it.
    condition_id: str
    question: str
    failure_type: str


def failure_check(
    *,
    condition_id: str,
    question: str,
    failure_type: str,
) -> ConditionSpec:
    return ConditionSpec(
        condition_id=condition_id,
        question=question,
        failure_type=failure_type,
    )


class ActionWithConditions(PickAction):
    preconditions: tuple[ConditionSpec, ...] = ()
    # Hold conditions are re-checked on every tick while a timed action is running.
    hold_conditions: tuple[ConditionSpec, ...] = ()
    postconditions: tuple[ConditionSpec, ...] = ()

    def _run_conditions(self, phase: str, conditions: tuple[ConditionSpec, ...]) -> py_trees.common.Status:
        for condition in conditions:
            self.controller.set_current_step(self.name)
            self.controller.set_current_condition(condition.condition_id, phase, condition.question)
            result = self.controller.check(condition.condition_id, condition.question)

            if result:
                continue

            self.controller.detect_failure(
                [condition.failure_type],
                fallback=condition.failure_type,
            )

            self.controller.set_current_condition(None, None)
            return py_trees.common.Status.FAILURE

        self.controller.set_current_condition(None, None)
        return py_trees.common.Status.SUCCESS

    def on_conditions_satisfied(self) -> None:
        pass


class TimedInterruptibleAction(ActionWithConditions):
    runtime_failures: tuple[str, ...] = RUNTIME_FAILURE_TYPES

    def __init__(self, name: str, controller: Any, step_name: str, action_text: str):
        super().__init__(name, controller)
        self.step_name = step_name
        self.action_text = action_text
        self.start_time: Optional[float] = None
        self.action_started = False

    def initialise(self) -> None:
        self.start_time = None
        self.action_started = False

    def _start_action(self) -> None:
        self.start_time = time.monotonic()
        self.action_started = True
        self.controller.set_current_step(self.step_name)
        if hasattr(self.controller.action_monitor, "open"):
            self.controller.action_monitor.open()
        print(f"[Action] {self.action_text} ({ACTION_DURATION_SECONDS:.1f}s, press {ACTION_HOTKEY_HINT})")

    def update(self) -> py_trees.common.Status:
        if not self.action_started:
            status = self._run_conditions("pre", self.preconditions)
            if status != py_trees.common.Status.SUCCESS:
                return status
            self._start_action()

        if self.controller.should_evaluate_hold_conditions():
            hold_status = self._run_conditions("hold", self.hold_conditions)
            if hold_status != py_trees.common.Status.SUCCESS:
                self._close_monitor()
                return hold_status

        runtime_failure = self.controller.poll_runtime_failure(list(self.runtime_failures))
        if runtime_failure:
            self._close_monitor()
            return py_trees.common.Status.FAILURE

        detected_failure = self.controller.action_monitor.poll_failure()
        if detected_failure:
            self._close_monitor()
            return self.controller.set_action_failure(detected_failure, None)

        if self.start_time is None:
            self.start_time = time.monotonic()

        if time.monotonic() - self.start_time >= ACTION_DURATION_SECONDS:
            self._close_monitor()
            status = self._run_conditions("post", self.postconditions)
            if status != py_trees.common.Status.SUCCESS:
                return status
            self.controller.state["last_valid_bt_step"] = self.step_name
            self.on_conditions_satisfied()
            return py_trees.common.Status.SUCCESS

        return py_trees.common.Status.RUNNING

    def terminate(self, new_status: py_trees.common.Status) -> None:
        self._close_monitor()

    def on_success(self) -> None:
        pass

    def _close_monitor(self) -> None:
        if hasattr(self.controller.action_monitor, "close"):
            self.controller.action_monitor.close()


class InstantAction(ActionWithConditions):
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
        self.on_conditions_satisfied()
        return py_trees.common.Status.SUCCESS

    def perform_action(self) -> None:
        raise NotImplementedError
