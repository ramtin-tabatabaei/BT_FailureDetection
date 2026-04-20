from __future__ import annotations

from .base import PlaceObjectAgent


class PlaceInstantStateMonitorAgent(PlaceObjectAgent):
    """Cheap sensor → VLM (single frame) — monitors grip and contact state during placement."""

    name = "InstantStateMonitorAgent"
    modality = "sensor_to_vlm"
    description = (
        "Monitors instantaneous grip state and contact forces during placement. "
        "Detects dropped objects during transit and collisions during descent."
    )
    failure_types = ("object_dropped", "collision_on_descent")
    condition_ids = ("ObjectSecuredInGripper",)

    def check_grip_security(
        self,
        force_n: float = 11.5,
        slip_detected: bool = False,
    ) -> tuple[bool, str]:
        ok = force_n > 5.0 and not slip_detected
        return ok, (
            f"Object is securely held for transit — {force_n:.1f} N, no slip detected."
            if ok else
            f"Grip insecure — force {force_n:.1f} N, slip_detected={slip_detected}."
        )

    def check_collision_on_descent(
        self,
        z_force_delta_n: float = 2.1,
        lateral_torque_nm: float = 0.04,
        spike_detected: bool = False,
    ) -> tuple[bool, str]:
        ok = not spike_detected and lateral_torque_nm < 0.5
        return ok, (
            f"Surface contact nominal — Δz {z_force_delta_n:.1f} N, "
            f"lateral torque {lateral_torque_nm:.2f} Nm."
            if ok else
            f"Collision on descent — torque {lateral_torque_nm:.2f} Nm, "
            f"spike_detected={spike_detected}."
        )

