"""Interfaces para matching futuro baseado em RapidFuzz, sem acoplamento a ORM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class MatchResult:
    source: str
    candidate: str
    score: float
    strategy: str


class NameMatcher(Protocol):
    def match(self, source: str, candidates: Sequence[str]) -> MatchResult | None: ...
