"""Contrato para futura persistência do catálogo no Django ORM."""

from __future__ import annotations

from typing import Protocol

from .models import Inventory


class CatalogBuilder(Protocol):
    def build(self, inventory: Inventory) -> None:
        """Persistirá GrupoMuscular, VideoExercicio e VariacaoExercicio no futuro."""
