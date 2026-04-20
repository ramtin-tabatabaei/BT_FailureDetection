from __future__ import annotations

# Failure types for PlaceObject task.
# Mirrors the structure of pickobject/failures.py.
# - monitor_during_actions: poll this failure continuously while timed actions run
FAILURE_RULES: dict[str, dict] = {
    "placement_location_blocked": {},
    "object_dropped":             {"monitor_during_actions": True},
    "placement_misaligned":       {},
    "collision_on_descent":       {"monitor_during_actions": True},
    "freezing":                   {"monitor_during_actions": True},
    "action_timeout":             {"monitor_during_actions": True},
    "execution_mismatch":         {},
}

RUNTIME_FAILURE_TYPES: tuple[str, ...] = tuple(
    ft for ft, rules in FAILURE_RULES.items()
    if rules.get("monitor_during_actions", False)
)

# Recovery options and retry budgets per failure type.
FAILURE_CONFIG: dict[str, dict] = {
    "placement_location_blocked": {
        "description": "The intended placement location is blocked or not visible.",
        "recoveries": ["retry_approach", "choose_alternate_location", "abort"],
        "retry_budget": 2,
    },
    "object_dropped": {
        "description": "The object was dropped during transport to the place location.",
        "recoveries": ["abort"],
        "retry_budget": 1,
    },
    "placement_misaligned": {
        "description": "The robot is not correctly aligned with the target placement pose.",
        "recoveries": ["retry_align", "retry_approach", "abort"],
        "retry_budget": 2,
    },
    "collision_on_descent": {
        "description": "A collision was detected while lowering the object onto the target.",
        "recoveries": ["retry_lower", "choose_alternate_location", "abort"],
        "retry_budget": 2,
    },
    "freezing": {
        "description": "The robot stopped moving unexpectedly during a place action.",
        "recoveries": ["retry_action", "abort"],
        "retry_budget": 2,
    },
    "action_timeout": {
        "description": "A place action exceeded its allowed execution time.",
        "recoveries": ["retry_action", "abort"],
        "retry_budget": 2,
    },
    "execution_mismatch": {
        "description": "A pre- or post-condition did not match the expected state after a place action.",
        "recoveries": ["retry_action", "retry_approach", "abort"],
        "retry_budget": 2,
    },
}

__all__ = ["FAILURE_RULES", "FAILURE_CONFIG", "RUNTIME_FAILURE_TYPES"]
