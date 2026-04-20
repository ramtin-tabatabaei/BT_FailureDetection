from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YesNoDecision:
    answer: bool
    explanation: str


@dataclass(frozen=True)
class ConditionAnswer:
    condition_id: str
    question: str
    answer: bool
    explanation: str


@dataclass(frozen=True)
class ConditionVerification:
    current_action: str
    next_action: str | None
    conditions: tuple[ConditionAnswer, ...]
    summary: str

    @property
    def all_satisfied(self) -> bool:
        return all(condition.answer for condition in self.conditions)


@dataclass(frozen=True)
class PoseVerification:
    check: str
    metric: str
    value: str
    threshold: str
    within: bool
    vlm_needed: bool = False
    vlm_explanation: str = ""


@dataclass(frozen=True)
class TemporalFrame:
    index: int
    moving: bool
    note: str


@dataclass(frozen=True)
class TemporalMonitoring:
    action: str
    frames: tuple[TemporalFrame, ...]
    freezing_detected: bool = False
    timeout_detected: bool = False


@dataclass(frozen=True)
class InstantReading:
    label: str
    value: str
    ok: bool


@dataclass(frozen=True)
class InstantStateCheck:
    check_label: str
    readings: tuple[InstantReading, ...]
    vlm_needed: bool = False
    vlm_explanation: str = ""


@dataclass(frozen=True)
class RecoveryDecision:
    chosen_recovery: str
    reasoning: str
