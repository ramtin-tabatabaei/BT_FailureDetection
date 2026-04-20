from __future__ import annotations

from .base import PickObjectAgent


class PickPoseVerificationAgent(PickObjectAgent):
    """Cheap model → VLM — verifies robot/object pose alignment."""

    name = "PoseVerificationAgent"
    modality = "cheap_to_vlm"
    description = "Verifies robot/object pose alignment for pre-grasp and grasp execution."
    failure_types = ("wrong_position", "wrong_orientation", "execution_mismatch")
    condition_ids = (
        "PreGraspPoseConfirmed",
        "GraspPositionAligned",
        "GraspOrientationAligned",
    )

    def check_position(
        self,
        position_error_mm: float = 8.2,
        threshold_mm: float = 15.0,
    ) -> tuple[bool, str]:
        within = position_error_mm <= threshold_mm
        return within, (
            f"Position error {position_error_mm:.1f} mm is within the "
            f"{threshold_mm:.0f} mm threshold."
            if within else
            f"Position error {position_error_mm:.1f} mm exceeds the "
            f"{threshold_mm:.0f} mm threshold — pose correction required."
        )

    def check_orientation(
        self,
        angle_error_deg: float = 1.8,
        threshold_deg: float = 5.0,
    ) -> tuple[bool, str]:
        within = angle_error_deg <= threshold_deg
        return within, (
            f"Orientation error {angle_error_deg:.1f}° is within the "
            f"{threshold_deg:.0f}° threshold."
            if within else
            f"Orientation error {angle_error_deg:.1f}° exceeds the "
            f"{threshold_deg:.0f}° threshold — reorientation required."
        )

