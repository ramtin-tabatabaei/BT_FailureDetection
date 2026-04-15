from __future__ import annotations

from .base import TimedInterruptibleAction


class OpenGripper(TimedInterruptibleAction):
    def __init__(self, name: str, controller):
        super().__init__(name, controller, "OpenGripper", "Opening gripper")
