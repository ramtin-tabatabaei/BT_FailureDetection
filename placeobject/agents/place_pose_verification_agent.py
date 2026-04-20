from __future__ import annotations

from .base import PlaceObjectAgent


class PlacePoseVerificationAgent(PlaceObjectAgent):
    """Cheap model → VLM — verifies robot pose at placement location and object height."""

    name = "PoseVerificationAgent"
    modality = "cheap_to_vlm"
    description = (
        "Verifies robot alignment at the placement location and object height "
        "above surface. Uses cheap geometric model first; escalates to VLM on anomaly."
    )
    failure_types = ("placement_misaligned",)
    condition_ids = ("AtPlaceLocation", "ObjectAtPlaceHeight")

    def check_position(
        self,
        position_error_mm: float = 5.4,
        threshold_mm: float = 10.0,
    ) -> tuple[bool, str]:
        within = position_error_mm <= threshold_mm
        return within, (
            f"Robot is correctly positioned above placement location — "
            f"error {position_error_mm:.1f} mm within {threshold_mm:.0f} mm threshold."
            if within else
            f"Placement position error {position_error_mm:.1f} mm exceeds "
            f"{threshold_mm:.0f} mm threshold — realigning."
        )

    def check_height(
        self,
        height_error_mm: float = 1.2,
        threshold_mm: float = 3.0,
    ) -> tuple[bool, str]:
        within = height_error_mm <= threshold_mm
        return within, (
            f"Object is at correct placement height — "
            f"error {height_error_mm:.1f} mm within {threshold_mm:.0f} mm threshold."
            if within else
            f"Height error {height_error_mm:.1f} mm exceeds "
            f"{threshold_mm:.0f} mm threshold — adjustment required."
        )

