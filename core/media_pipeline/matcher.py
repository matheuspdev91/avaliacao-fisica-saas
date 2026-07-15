"""Interfaces para matching futuro baseado em RapidFuzz, sem acoplamento a ORM."""

from __future__ import annotations

from typing import Protocol, Sequence

from .models import Exercise, MatchResult, Variation


class NameMatcher(Protocol):
    def match(
        self,
        exercise: Exercise,
        variations: Sequence[Variation],
    ) -> MatchResult | None: ...
