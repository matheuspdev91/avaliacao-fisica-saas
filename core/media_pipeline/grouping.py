"""Contratos para agrupamento por corpus; implementação será adicionada depois."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .inventory import MediaAsset


@dataclass(frozen=True, slots=True)
class ExerciseCluster:
    canonical_name: str
    assets: tuple[MediaAsset, ...]
    confidence: float


class AssetGrouper(Protocol):
    def group(self, assets: Sequence[MediaAsset]) -> tuple[ExerciseCluster, ...]: ...
