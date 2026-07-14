"""Contrato para futura persistência do catálogo no Django ORM."""

from __future__ import annotations

from typing import Protocol

from .inventory import MediaInventory


class CatalogBuilder(Protocol):
    def build(self, inventory: MediaInventory) -> None:
        """Persistirá GrupoMuscular, VideoExercicio e VariacaoExercicio no futuro."""
