from __future__ import annotations

import select
import sys
import termios
import tty
from typing import Dict, List, Optional, Protocol

from .config import ACTION_HOTKEY_FAILURES


class ConditionProvider(Protocol):
    def check(self, check_name: str, description: str, state: Dict[str, object]) -> bool:
        ...


class ChoiceProvider(Protocol):
    def choose(
        self,
        prompt: str,
        options: List[str],
        descriptions: Dict[str, str],
        state: Dict[str, object],
        input_prompt: str,
    ) -> str:
        ...


class ActionMonitor(Protocol):
    def poll_failure(self) -> Optional[str]:
        ...


class TerminalConditionProvider:
    def __init__(self):
        self.evaluate_hold_conditions = False
        self._cached_tick_id: Optional[int] = None
        self._cached_conditions: Dict[str, bool] = {}

    def clear(self) -> None:
        self._cached_tick_id = None
        self._cached_conditions.clear()

    def _prepare_cache(self, state: Dict[str, object]) -> None:
        tick_id = int(state.get("tick_count", 0))
        if self._cached_tick_id == tick_id:
            return
        self._cached_tick_id = tick_id
        self._cached_conditions.clear()

    def check(self, check_name: str, description: str, state: Dict[str, object]) -> bool:
        phase = state.get("current_condition_phase")
        can_reuse_answer = phase in {"pre", "post"}
        if can_reuse_answer:
            self._prepare_cache(state)
            if check_name in self._cached_conditions:
                result = self._cached_conditions[check_name]
                cached_answer = "y" if result else "n"
                print(f"[CHECK] {check_name} - reusing cached answer: {cached_answer}")
                return result

        while True:
            raw = input(f"[CHECK] {check_name} - {description} (y/n): ").strip().lower()
            if raw in ("y", "yes"):
                if can_reuse_answer:
                    self._cached_conditions[check_name] = True
                return True
            if raw in ("n", "no"):
                if can_reuse_answer:
                    self._cached_conditions[check_name] = False
                return False
            print("  Please answer y or n.")


class TerminalChoiceProvider:
    def choose(
        self,
        prompt: str,
        options: List[str],
        descriptions: Dict[str, str],
        state: Dict[str, object],
        input_prompt: str,
    ) -> str:
        while True:
            print(prompt)
            for index, option in enumerate(options, start=1):
                description = descriptions.get(option, "")
                if description:
                    print(f"  {index}. {option} - {description}")
                else:
                    print(f"  {index}. {option}")

            raw = input(input_prompt).strip()
            if raw.isdigit():
                choice_index = int(raw) - 1
                if 0 <= choice_index < len(options):
                    return options[choice_index]
            if raw in options:
                return raw
            print("  Please choose one of the listed options.")


class ScriptedConditionProvider:
    """Condition provider for scripted/MCP-driven runs.

    All conditions default to ``True`` (success) unless explicitly overridden
    via :meth:`set_response`.  This means an agent only needs to set the
    conditions it wants to *fail*; everything else passes automatically.
    """

    def __init__(self, default_to_success: bool = True):
        self.evaluate_hold_conditions = True
        self.responses: Dict[str, bool] = {}
        self.default_to_success = default_to_success

    def set_response(self, check_name: str, value: bool) -> None:
        self.responses[check_name] = value

    def clear(self) -> None:
        self.responses.clear()

    def check(self, check_name: str, description: str, state: Dict[str, object]) -> bool:
        if check_name in self.responses:
            return self.responses[check_name]
        return self.default_to_success


class ScriptedChoiceProvider:
    def __init__(self):
        self.choices: Dict[str, str] = {}

    def set_choice(self, prompt_key: str, value: str) -> None:
        self.choices[prompt_key] = value

    def clear(self) -> None:
        self.choices.clear()

    def choose(
        self,
        prompt: str,
        options: List[str],
        descriptions: Dict[str, str],
        state: Dict[str, object],
        input_prompt: str,
    ) -> str:
        prompt_key = str(state.get("pending_prompt_key") or prompt)
        choice = self.choices.get(prompt_key)
        if choice not in options:
            raise ValueError(f"No scripted choice configured for prompt '{prompt_key}'")
        return choice


class NullActionMonitor:
    def poll_failure(self) -> Optional[str]:
        return None


class TerminalKeyMonitor:
    def __init__(self):
        self.enabled = False
        self.fd: Optional[int] = None
        self.original_attrs = None

    def open(self) -> None:
        self.enabled = sys.stdin.isatty()
        if self.enabled:
            self.fd = sys.stdin.fileno()
            self.original_attrs = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)

    def close(self) -> None:
        if self.enabled and self.fd is not None and self.original_attrs is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.original_attrs)
        self.enabled = False
        self.fd = None
        self.original_attrs = None

    def poll_failure(self) -> Optional[str]:
        if not self.enabled:
            return None
        readable, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not readable:
            return None
        key = sys.stdin.read(1).lower()
        return ACTION_HOTKEY_FAILURES.get(key)


class InteractiveActionMonitor(NullActionMonitor):
    def __init__(self):
        self.monitor = TerminalKeyMonitor()

    def open(self) -> None:
        self.monitor.open()

    def close(self) -> None:
        self.monitor.close()

    def poll_failure(self) -> Optional[str]:
        return self.monitor.poll_failure()
