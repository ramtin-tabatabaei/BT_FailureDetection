from __future__ import annotations

# Define each failure once here.
# Optional flags:
# - monitor_during_actions: poll this failure continuously while timed actions run
# - hotkey: terminal-mode manual injection key
FAILURE_RULES = {
    "object_not_found": {},
    "wrong_object_selection": {},
    "wrong_position": {},
    "wrong_orientation": {},
    "execution_mismatch": {"hotkey": "x"},
    "freezing": {"monitor_during_actions": True, "hotkey": "f"},
    "grip_loss": {"monitor_during_actions": True, "hotkey": "g"},
    "collision": {"monitor_during_actions": True, "hotkey": "c"},
    "force_limit_exceeded": {"monitor_during_actions": True, "hotkey": "l"},
    "action_timeout": {"monitor_during_actions": True, "hotkey": "t"},
}

RUNTIME_FAILURE_TYPES = tuple(
    failure_type
    for failure_type, rules in FAILURE_RULES.items()
    if rules.get("monitor_during_actions", False)
)

HOTKEY_FAILURE_TYPES = {
    rules["hotkey"]: failure_type
    for failure_type, rules in FAILURE_RULES.items()
    if "hotkey" in rules
}


def build_hotkey_hint(mapping: dict[str, str]) -> str:
    labels = []
    for key, failure_type in mapping.items():
        if failure_type == "force_limit_exceeded":
            label = "force_limit"
        elif failure_type == "execution_mismatch":
            label = "exec_mismatch"
        else:
            label = failure_type
        labels.append(f"{key}={label}")
    return ", ".join(labels)


__all__ = [
    "FAILURE_RULES",
    "HOTKEY_FAILURE_TYPES",
    "RUNTIME_FAILURE_TYPES",
    "build_hotkey_hint",
]
