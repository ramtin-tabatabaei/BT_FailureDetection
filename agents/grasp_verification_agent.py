from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from .base import YesNoDecision
from .scene_perception_agent import _load_api_key


class GraspVerificationAgent:
    """VLM-based agent that verifies the selected grasp target from a wrist camera image.

    This is the real implementation of the GraspVerificationAgent described in
    the project architecture. It asks a vision model whether the object visible
    in the wrist camera frame matches the requested target description.

    If no API key is available, callers are expected to fall back to
    :meth:`predict` for demo mode.
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

    def check(
        self,
        image_path: str,
        target_description: str = "target object",
    ) -> tuple[bool, str]:
        """Check whether the object in the wrist camera frame matches the target.

        Returns
        -------
        (is_correct, explanation)
            is_correct   : True if the VLM confirms the object matches the target
            explanation  : the VLM's one-sentence reasoning
        """
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

        prompt = (
            "You are a robot grasp verification module. "
            "Look at the wrist camera image and answer ONE question:\n\n"
            f"Does the object that the gripper is about to close on match the "
            f"target description '{target_description}'?\n\n"
            "Reply with exactly two lines:\n"
            "ANSWER: YES  or  ANSWER: NO\n"
            "REASON: <one sentence explaining what you see>"
        )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=128,
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
        is_correct = "ANSWER: YES" in text.upper()

        explanation = text
        for line in text.splitlines():
            if line.upper().startswith("REASON:"):
                explanation = line.split(":", 1)[-1].strip()
                break

        return is_correct, explanation

    @staticmethod
    def predict(
        target_description: str,
        *,
        is_correct: bool,
    ) -> YesNoDecision:
        """Return a deterministic demo prediction without calling the API."""
        if is_correct:
            explanation = (
                f"The object visible in the wrist camera frame matches the target "
                f"description '{target_description}', so the correct object is selected."
            )
        else:
            explanation = (
                f"The object visible in the wrist camera frame does not match the target "
                f"description '{target_description}', so the wrong object is being approached."
            )
        return YesNoDecision(answer=is_correct, explanation=explanation)
