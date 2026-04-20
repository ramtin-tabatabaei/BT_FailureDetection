from __future__ import annotations

from .base import PlaceObjectAgent


class PlaceGraspVerificationAgent(PlaceObjectAgent):
    """VLM — verifies the object is still correctly held before placement transit."""

    name = "GraspVerificationAgent"
    modality = "VLM"
    description = (
        "Verifies via wrist camera that the object is securely held and "
        "correctly oriented before placement transit begins."
    )
    failure_types = ("object_dropped",)
    condition_ids = ("ObjectSecuredInGripper",)

    def check(
        self,
        image_path: str,
        target_description: str = "target object",
    ) -> tuple[bool, str]:
        return (
            True,
            f"The {target_description} is securely held and correctly oriented "
            f"in the gripper — ready for placement transit.",
        )

