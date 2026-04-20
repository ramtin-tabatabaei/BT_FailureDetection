from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentSpec:
    name: str
    modality: str
    description: str
    failure_types: tuple[str, ...]
    condition_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class PickObjectAgent:
    name: str = ""
    modality: str = ""
    description: str = ""
    failure_types: tuple[str, ...] = ()
    condition_ids: tuple[str, ...] = ()

    @classmethod
    def spec(cls) -> AgentSpec:
        return AgentSpec(
            name=cls.name,
            modality=cls.modality,
            description=cls.description,
            failure_types=cls.failure_types,
            condition_ids=cls.condition_ids,
        )
