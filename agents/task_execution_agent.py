from __future__ import annotations

from orchestrator import PickAndPlaceOrchestrator


class TaskExecutionAgent:
    """LLM task agent wrapper around the orchestrator's execution tools."""

    def __init__(self, orchestrator: PickAndPlaceOrchestrator) -> None:
        self.orchestrator = orchestrator

    def get_summary(self) -> dict[str, object]:
        return self.orchestrator.get_task_summary()

    def describe_pick_tree(self) -> str:
        return self.orchestrator.pick_controller.describe_tree()

    def describe_place_tree(self) -> str:
        return self.orchestrator.place_controller.describe_tree()

    def tick_current(self) -> dict[str, object]:
        return self.orchestrator.tick_current()

    def advance_phase(self) -> dict[str, object]:
        return self.orchestrator.advance_phase()

    def get_combined_log(self) -> list[dict[str, object]]:
        return self.orchestrator.get_combined_history()
