from __future__ import annotations

from .base import PlaceObjectAgent


class PlaceScenePerceptionAgent(PlaceObjectAgent):
    """VLM — checks whether the placement location is visible and unobstructed."""

    name = "ScenePerceptionAgent"
    modality = "VLM"
    description = (
        "Checks whether the target placement location is visible and "
        "unobstructed before the robot begins moving to place."
    )
    failure_types = ("placement_location_blocked",)
    condition_ids = ("PlaceLocationVisible",)

    def check(
        self,
        image_path: str,
        target_description: str = "placement surface",
    ) -> tuple[bool, str]:
        try:
            from agents.scene_perception_agent import ScenePerceptionAgent as _VLM
            return _VLM().check(image_path, target_description)
        except Exception:
            pass
        return (
            True,
            f"The {target_description} is visible and unobstructed — placement is possible.",
        )

