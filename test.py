from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Hardcoded paths — update these if your files move
# ---------------------------------------------------------------------------
DEFAULT_IMAGE_PATH = (
    "/Users/stabatabaeim/Univerisity/Year 3/BT Study/Codes/TestImage.png"
)
DEFAULT_API_KEY_PATH = (
    "/Users/stabatabaeim/Univerisity/Year 3/BT Study/Codes/api_key.txt"
)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Minimal standalone base types (replaces .base import)
# ---------------------------------------------------------------------------

@dataclass
class ConditionAnswer:
    condition_id: str
    question: str
    answer: bool
    explanation: str


@dataclass
class ConditionVerification:
    current_action: str
    next_action: Optional[str]
    conditions: Tuple[ConditionAnswer, ...]
    summary: str

    @property
    def all_satisfied(self) -> bool:
        return all(c.answer for c in self.conditions)


@dataclass
class YesNoDecision:
    answer: bool
    explanation: str


class PickObjectAgent:
    """Minimal base class — override in your BT framework as needed."""
    name: str = ""
    modality: str = ""
    description: str = ""
    failure_types: tuple = ()
    condition_ids: tuple = ()


# ---------------------------------------------------------------------------


def _load_api_key(api_key: Optional[str] = None) -> Optional[str]:
    if api_key:
        return api_key
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key
    # Try the hardcoded path first, then fall back to local api_key.txt
    for key_file in [Path(DEFAULT_API_KEY_PATH), Path("api_key.txt")]:
        if key_file.exists():
            return key_file.read_text().strip()
    return None


class ExecutionVerificationAgent:
    """VLM-based agent for visual transition checks between BT actions.

    The agent inspects a single image captured at a stage boundary and answers:
    - post-conditions of the current action
    - pre-conditions of the next action, if a next action exists

    If no API key or image is available, callers should fall back to
    :meth:`predict`.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        try:
            import anthropic as _anthropic
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        resolved_key = _load_api_key(api_key)
        if not resolved_key:
            raise RuntimeError(
                "No API key found. Add it to api_key.txt or set "
                "ANTHROPIC_API_KEY environment variable."
            )

        self._client = _anthropic.Anthropic(api_key=resolved_key)
        self.model = model

    def check_transition(
        self,
        image_path: str,
        *,
        current_action: str,
        current_post_conditions: list[tuple[str, str]] | None = None,
        next_action: str | None = None,
        next_pre_conditions: list[tuple[str, str]] | None = None,
    ) -> ConditionVerification:
        """Verify transition conditions from one image.

        Parameters
        ----------
        image_path:
            Path to the scene / wrist-camera image captured at the transition.
        current_action:
            The BT action that has just completed or is being validated.
        current_post_conditions:
            ``[(condition_id, question), ...]`` for the current action's
            post-conditions.
        next_action:
            Optional name of the next BT action.
        next_pre_conditions:
            ``[(condition_id, question), ...]`` for the next action's
            pre-conditions.
        """
        if not image_path:
            raise RuntimeError("An image_path is required for VLM execution verification.")

        post_conditions = list(current_post_conditions or [])
        pre_conditions = list(next_pre_conditions or [])
        all_conditions = post_conditions + pre_conditions
        if not all_conditions:
            raise RuntimeError("No conditions were provided for transition verification.")

        image_bytes = Path(image_path).read_bytes()
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        suffix = Path(image_path).suffix.lower()
        media_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_map.get(suffix, "image/jpeg")

        prompt = self._build_prompt(
            current_action=current_action,
            current_post_conditions=post_conditions,
            next_action=next_action,
            next_pre_conditions=pre_conditions,
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        text = response.content[0].text.strip()
        payload = self._parse_json_payload(text)

        by_id = {
            item["condition_id"]: item
            for item in payload.get("conditions", [])
            if isinstance(item, dict) and "condition_id" in item
        }

        parsed_conditions: list[ConditionAnswer] = []
        for condition_id, question in all_conditions:
            item = by_id.get(condition_id, {})
            parsed_conditions.append(
                ConditionAnswer(
                    condition_id=condition_id,
                    question=question,
                    answer=bool(item.get("answer", False)),
                    explanation=str(
                        item.get(
                            "explanation",
                            "No explanation returned by the execution-verification model.",
                        )
                    ),
                )
            )

        summary = str(
            payload.get(
                "summary",
                "Execution-verification model returned no summary.",
            )
        )

        return ConditionVerification(
            current_action=current_action,
            next_action=next_action,
            conditions=tuple(parsed_conditions),
            summary=summary,
        )

    @staticmethod
    def predict(
        *,
        current_action: str,
        current_post_conditions: list[tuple[str, str]] | None = None,
        next_action: str | None = None,
        next_pre_conditions: list[tuple[str, str]] | None = None,
        condition_answers: dict[str, bool] | None = None,
    ) -> ConditionVerification:
        """Return deterministic demo predictions without calling the API."""
        answers = condition_answers or {}
        post_conditions = list(current_post_conditions or [])
        pre_conditions = list(next_pre_conditions or [])
        all_conditions = post_conditions + pre_conditions

        parsed_conditions: list[ConditionAnswer] = []
        for condition_id, question in all_conditions:
            answer = answers.get(condition_id, True)
            if answer:
                explanation = (
                    f"{condition_id} appears satisfied in the current transition image."
                )
            else:
                explanation = (
                    f"{condition_id} does not appear satisfied in the current transition image."
                )
            parsed_conditions.append(
                ConditionAnswer(
                    condition_id=condition_id,
                    question=question,
                    answer=answer,
                    explanation=explanation,
                )
            )

        if all(condition.answer for condition in parsed_conditions):
            if next_action:
                summary = (
                    f"The post-conditions for {current_action} and pre-conditions for "
                    f"{next_action} are visually consistent."
                )
            else:
                summary = f"The checked post-conditions for {current_action} are visually consistent."
        else:
            failed_ids = [c.condition_id for c in parsed_conditions if not c.answer]
            summary = (
                f"Execution transition check failed after {current_action}: "
                f"{', '.join(failed_ids)} not visually confirmed."
            )

        return ConditionVerification(
            current_action=current_action,
            next_action=next_action,
            conditions=tuple(parsed_conditions),
            summary=summary,
        )

    def verify_conditions(
        self,
        *,
        action: str,
        phase: str,
        conditions: list[tuple[str, bool]],
    ) -> ConditionVerification:
        """Compatibility helper for the older demo API."""
        questionized_conditions = [
            (condition_id, f"Is {condition_id} satisfied for {action} ({phase})?")
            for condition_id, _ in conditions
        ]
        answers = {condition_id: answer for condition_id, answer in conditions}
        if phase == "post":
            return self.predict(
                current_action=action,
                current_post_conditions=questionized_conditions,
                condition_answers=answers,
            )
        return self.predict(
            current_action=action,
            next_action=action,
            next_pre_conditions=questionized_conditions,
            condition_answers=answers,
        )

    def confirm_placement(
        self,
        *,
        confirmed: bool,
        reason: str | None = None,
    ) -> YesNoDecision:
        if reason is None:
            if confirmed:
                reason = "The object is resting stably on the placement surface."
            else:
                reason = "The object is not stably resting on the placement surface."
        return YesNoDecision(answer=confirmed, explanation=reason)

    def _build_prompt(
        self,
        *,
        current_action: str,
        current_post_conditions: list[tuple[str, str]],
        next_action: str | None,
        next_pre_conditions: list[tuple[str, str]],
    ) -> str:
        lines = [
            "You are a robot execution-verification module.",
            "Inspect the single image and decide which behaviour-tree conditions are visually satisfied.",
            "",
            f"Current action: {current_action}",
        ]
        if current_post_conditions:
            lines.append("Current action post-conditions to verify:")
            for condition_id, question in current_post_conditions:
                lines.append(f"- {condition_id}: {question}")
        if next_action:
            lines.append("")
            lines.append(f"Next action: {next_action}")
        if next_pre_conditions:
            lines.append("Next action pre-conditions to verify:")
            for condition_id, question in next_pre_conditions:
                lines.append(f"- {condition_id}: {question}")

        lines.extend(
            [
                "",
                "Return JSON only with this schema:",
                "{",
                '  "conditions": [',
                '    {"condition_id": "...", "answer": true, "explanation": "one sentence"},',
                '    {"condition_id": "...", "answer": false, "explanation": "one sentence"}',
                "  ],",
                '  "summary": "one sentence overall summary"',
                "}",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _parse_json_payload(text: str) -> dict[str, object]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end < start:
                raise RuntimeError("Execution-verification model did not return JSON.") from None
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "Execution-verification model returned malformed JSON."
                ) from exc


class PickExecutionVerificationAgent(PickObjectAgent):
    """Cheap model → VLM — verifies stage transitions for the PickObject BT."""

    name = "ExecutionVerificationAgent"
    modality = "cheap_to_vlm"
    description = (
        "Verifies, from one transition image, that the current stage's post-conditions "
        "and the next stage's pre-conditions are visually coherent."
    )
    failure_types = ("execution_mismatch",)
    condition_ids = (
        "GripperReadyBeforeGrasp",
        "GripperReady",
        "PreGraspPoseConfirmed",
    )

    def check_transition(
        self,
        image_path: str,
        *,
        current_action: str,
        current_post_conditions: list[tuple[str, str]] | None = None,
        next_action: str | None = None,
        next_pre_conditions: list[tuple[str, str]] | None = None,
        predicted_answers: dict[str, bool] | None = None,
    ) -> ConditionVerification:
        """Try VLM verification first, fall back to deterministic predict() on failure."""
        try:
            return ExecutionVerificationAgent().check_transition(
                image_path,
                current_action=current_action,
                current_post_conditions=current_post_conditions,
                next_action=next_action,
                next_pre_conditions=next_pre_conditions,
            )
        except Exception:
            return ExecutionVerificationAgent.predict(
                current_action=current_action,
                current_post_conditions=current_post_conditions,
                next_action=next_action,
                next_pre_conditions=next_pre_conditions,
                condition_answers=predicted_answers,
            )

    def verify(
        self,
        action: str,
        phase: str,
        conditions: list[tuple[str, bool]],
    ) -> tuple[bool, str]:
        """Simplified interface returning (all_satisfied, summary)."""
        condition_specs = [
            (condition_id, f"Is {condition_id} satisfied for {action} ({phase})?")
            for condition_id, _ in conditions
        ]
        predicted_answers = {condition_id: answer for condition_id, answer in conditions}
        if phase == "post":
            verification = self.check_transition(
                "",
                current_action=action,
                current_post_conditions=condition_specs,
                predicted_answers=predicted_answers,
            )
        else:
            verification = self.check_transition(
                "",
                current_action=action,
                next_action=action,
                next_pre_conditions=condition_specs,
                predicted_answers=predicted_answers,
            )
        return verification.all_satisfied, verification.summary

# ---------------------------------------------------------------------------
# Run directly:  python execution_verification_agent.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = ExecutionVerificationAgent()

    result = agent.check_transition(
        DEFAULT_IMAGE_PATH,
        current_action="GraspObject",
        current_post_conditions=[
            ("GripperReady", "Is the gripper open and ready?"),
            ("PreGraspPoseConfirmed", "Is the arm in pre-grasp position?"),
        ],
        next_action="LiftObject",
        next_pre_conditions=[
            ("GripperReadyBeforeGrasp", "Is the gripper confirmed ready before grasping?"),
        ],
    )

    print("=" * 60)
    print(f"Summary: {result.summary}")
    print(f"All satisfied: {result.all_satisfied}")
    print("-" * 60)
    for c in result.conditions:
        status = "✓" if c.answer else "✗"
        print(f"  [{status}] {c.condition_id}")
        print(f"       Q: {c.question}")
        print(f"       A: {c.explanation}")
    print("=" * 60)