from __future__ import annotations

from .base import PoseVerification


class PoseVerificationAgent:
    """Demo-facing pose agent that predicts pass/fail from provided metrics."""

    def verify(
        self,
        *,
        check: str,
        metric: str,
        value: str,
        threshold: str,
        within: bool,
        vlm_needed: bool = False,
        vlm_reason: str = "",
    ) -> PoseVerification:
        return PoseVerification(
            check=check,
            metric=metric,
            value=value,
            threshold=threshold,
            within=within,
            vlm_needed=vlm_needed,
            vlm_explanation=vlm_reason,
        )
