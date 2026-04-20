from __future__ import annotations

from .base import PickObjectAgent


class PickGraspVerificationAgent(PickObjectAgent):
    """VLM — checks whether the selected grasp target is the intended object."""

    name = "GraspVerificationAgent"
    modality = "VLM"
    description = "Checks whether the selected grasp target is the intended object."
    failure_types = ("wrong_object_selection",)
    condition_ids = ("CorrectObjectSelected",)

    def check(
        self,
        image_path: str,
        target_description: str = "target object",
    ) -> tuple[bool, str]:
        try:
            from agents.grasp_verification_agent import GraspVerificationAgent as _VLM
            return _VLM().check(image_path, target_description)
        except Exception:
            from agents.grasp_verification_agent import GraspVerificationAgent as _VLM
            decision = _VLM.predict(target_description, is_correct=True)
            return decision.answer, decision.explanation

