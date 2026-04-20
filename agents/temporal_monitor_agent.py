from __future__ import annotations

from .base import TemporalFrame, TemporalMonitoring


class TemporalMonitorAgent:
    """Demo-facing runtime monitor for freezing and timeout-like temporal failures."""

    def monitor(
        self,
        *,
        action: str,
        n_frames: int = 3,
        frozen: bool = False,
        timeout: bool = False,
    ) -> TemporalMonitoring:
        frames: list[TemporalFrame] = []
        for index in range(1, n_frames + 1):
            moving = not (frozen and index == n_frames)
            if moving:
                note = "robot moving"
            else:
                note = "ROBOT NOT MOVING"
            frames.append(TemporalFrame(index=index, moving=moving, note=note))
        return TemporalMonitoring(
            action=action,
            frames=tuple(frames),
            freezing_detected=frozen,
            timeout_detected=timeout,
        )
