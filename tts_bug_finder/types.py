from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Seed:
    seed_id: str
    text: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MutationCandidate:
    text: str
    mutation_trace: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class QueueItem:
    text: str
    seed_id: str | None
    tags: tuple[str, ...]
    mutation_trace: str | None = None
    depth: int = 0

