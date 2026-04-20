from __future__ import annotations

from .base import PickObjectAgent


class PickInstantStateMonitorAgent(PickObjectAgent):
    """Cheap sensor → VLM (single frame) — monitors gripper and contact state."""

    name = "InstantStateMonitorAgent"
    modality = "sensor_to_vlm"
    description = "Checks instantaneous gripper and contact state from sensor snapshot."
    failure_types = ("grip_loss", "collision", "force_limit_exceeded", "execution_mismatch")
    condition_ids = (
        "GripperReady",
        "ObjectInGripper",
        "FinalObjectInGripperCheck",
    )

    def check_gripper_state(
        self,
        gripper_open: bool = True,
        fault: str = "none",
    ) -> tuple[bool, str]:
        ok = gripper_open and fault == "none"
        return ok, (
            "Gripper is open and fault-free — ready for approach."
            if ok else
            f"Gripper fault detected: {fault}."
        )

    def check_grip(
        self,
        force_n: float = 12.4,
        slip_detected: bool = False,
    ) -> tuple[bool, str]:
        ok = force_n > 5.0 and not slip_detected
        return ok, (
            f"Object is securely held — {force_n:.1f} N applied, no slip detected."
            if ok else
            f"Grip failure — force {force_n:.1f} N, slip_detected={slip_detected}."
        )

    def check_collision(
        self,
        lateral_torque_nm: float = 0.04,
        spike_detected: bool = False,
    ) -> tuple[bool, str]:
        ok = lateral_torque_nm < 0.5 and not spike_detected
        return ok, (
            f"No collision — lateral torque {lateral_torque_nm:.2f} Nm is nominal."
            if ok else
            f"Collision detected — torque {lateral_torque_nm:.2f} Nm, "
            f"spike_detected={spike_detected}."
        )

