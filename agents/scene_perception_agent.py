"""
ScenePerceptionAgent
====================
Real VLM-based agent that checks whether the target object is visible
in a scene image before any robot movement begins.

This is the implementation of the ScenePerceptionAgent described in the
system architecture.  It calls Claude Vision API with the scene image and
a structured yes/no question, then parses the response into a bool that
is injected into the BT via ``set_condition_response("TargetVisible", ...)``.

Usage::

    agent = ScenePerceptionAgent()           # reads api_key.txt or ANTHROPIC_API_KEY
    visible, explanation = agent.check("scene.jpg", "red coffee mug")
    controller.set_condition_response("TargetVisible", visible)

API key resolution (first match wins):
  1. api_key.txt  in the same directory as this file's project root
  2. ANTHROPIC_API_KEY  environment variable
  3. Passed directly as constructor argument
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_API_KEY_FILE = _PROJECT_ROOT / "api_key.txt"


def _load_api_key(api_key: Optional[str] = None) -> Optional[str]:
    if api_key:
        return api_key
    if _API_KEY_FILE.exists():
        key = _API_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    return os.environ.get("ANTHROPIC_API_KEY")


class ScenePerceptionAgent:
    """VLM-based agent: checks if a target object is visible in a scene image.

    Calls Claude Vision API with the image and a structured prompt.
    Returns (is_visible: bool, explanation: str).

    If no API key is available, raises RuntimeError — the caller should
    catch this and fall back to simulation.
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
        """Check whether ``target_description`` is visible in ``image_path``.

        Returns
        -------
        (is_visible, explanation)
            is_visible   : True if the VLM confirms the object is present
            explanation  : the VLM's one-sentence reasoning
        """
        image_bytes = Path(image_path).read_bytes()
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        suffix = Path(image_path).suffix.lower()
        media_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_map.get(suffix, "image/jpeg")

        prompt = (
            f"You are a robot perception module. "
            f"Look at the scene image and answer ONE question:\n\n"
            f"Is the '{target_description}' visible and reachable in the scene?\n\n"
            f"Reply with exactly two lines:\n"
            f"ANSWER: YES  or  ANSWER: NO\n"
            f"REASON: <one sentence explaining what you see>"
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
        is_visible = "ANSWER: YES" in text.upper()

        # Extract the REASON line if present.
        explanation = text
        for line in text.splitlines():
            if line.upper().startswith("REASON:"):
                explanation = line.split(":", 1)[-1].strip()
                break

        return is_visible, explanation

    @staticmethod
    def predict(
        target_description: str,
        *,
        visible: bool,
    ) -> tuple[bool, str]:
        """Return a deterministic demo prediction without calling the API."""
        if visible:
            explanation = f"The {target_description} is clearly visible in the foreground of the scene."
        else:
            explanation = (
                f"The {target_description} is not visible in the current camera frame — "
                "scene may need to be rescanned."
            )
        return visible, explanation
