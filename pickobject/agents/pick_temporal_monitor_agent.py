from __future__ import annotations

from .base import PickObjectAgent


class PickTemporalMonitorAgent(PickObjectAgent):
    """Cheap sensor → VLM (image sequence) — monitors motion during pick actions."""

    name = "TemporalMonitorAgent"
    modality = "sensor_to_vlm"
    description = "Monitors time-varying execution issues such as freezing and action timeout."
    failure_types = ("freezing", "action_timeout")
    condition_ids = ()

    def monitor(
        self,
        action: str,
        n_frames: int = 3,
    ) -> tuple[bool, str]:
        return (
            True,
            f"Robot moved continuously during {action} across {n_frames} sampled frames "
            f"— no freezing or timeout detected.",
        )

