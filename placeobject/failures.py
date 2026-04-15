from __future__ import annotations

# Failure types for PlaceObject task.
# Each key is the failure_type string used in condition specs and recovery configs.
FAILURE_RULES: dict[str, dict] = {
    "placement_location_blocked": {},
    "object_dropped": {},
    "placement_misaligned": {},
    "collision_on_descent": {"monitor_during_actions": True},
}

RUNTIME_FAILURE_TYPES: tuple[str, ...] = tuple(
    ft for ft, rules in FAILURE_RULES.items()
    if rules.get("monitor_during_actions", False)
)

# Recovery options and retry budgets per failure type.
FAILURE_CONFIG: dict[str, dict] = {
    "placement_location_blocked": {
        "description": "The intended placement location is blocked or unreachable.",
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
}

__all__ = ["FAILURE_RULES", "RUNTIME_FAILURE_TYPES", "FAILURE_CONFIG"]
