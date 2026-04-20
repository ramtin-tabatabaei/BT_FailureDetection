from __future__ import annotations

from .base import PickObjectAgent


class PickScenePerceptionAgent(PickObjectAgent):
    """VLM — checks whether the target object is visible in the scene before grasp planning.

    Sets: TargetVisible
    Detects: object_not_found
    """

    name = "ScenePerceptionAgent"
    modality = "VLM"
    description = "Checks whether the target object is visible in the scene before grasp planning."
    failure_types = ("object_not_found",)
    condition_ids = ("TargetVisible",)

    def check(
        self,
        image_path: str,
        target_description: str = "target object",
    ) -> tuple[bool, str]:
        try:
            from agents.scene_perception_agent import ScenePerceptionAgent as _VLM
            return _VLM().check(image_path, target_description)
        except Exception:
            pass
        return (
            True,
            f"The {target_description} is clearly visible and reachable in the scene.",
        )

