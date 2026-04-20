from __future__ import annotations

# Re-export the shared base classes from pickobject.
# FailureDetector and FailureSignal are generic — no need to duplicate them.
from pickobject.detectors.base import FailureDetector, FailureSignal

__all__ = ["FailureDetector", "FailureSignal"]
