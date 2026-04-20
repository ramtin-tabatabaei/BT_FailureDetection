from __future__ import annotations

from .base import InstantReading, InstantStateCheck


class InstantStateMonitorAgent:
    """Demo-facing instant state monitor for one-shot sensor or VLM checks."""

    def inspect(
        self,
        *,
        check_label: str,
        readings: list[tuple[str, str, bool]],
        vlm_needed: bool = False,
        vlm_reason: str = "",
    ) -> InstantStateCheck:
        return InstantStateCheck(
            check_label=check_label,
            readings=tuple(InstantReading(label, value, ok) for label, value, ok in readings),
            vlm_needed=vlm_needed,
            vlm_explanation=vlm_reason,
        )
