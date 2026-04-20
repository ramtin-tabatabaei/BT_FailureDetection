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


class PlaceObjectAgent:
    """Base class for all PlaceObject agents.

    Each subclass declares its metadata as class attributes.
    No logic lives here — agents are identified by name, modality,
    failure_types they can detect, and condition_ids they set.
    """

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
