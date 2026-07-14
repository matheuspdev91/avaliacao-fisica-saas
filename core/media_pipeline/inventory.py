"""Tipos e serialização do inventário de mídias."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True, slots=True)
class MediaAsset:
    """Um arquivo de mídia encontrado, sem qualquer dependência de banco."""

    category: str
    muscle_group: str
    filename: str
    original_name: str
    normalized_name: str
    extension: str
    size: int
    sha256: str
    path: Path

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["path"] = str(self.path)
        # Chaves em português preservam o formato que os scripts legados esperam.
        return {
            **data,
            "categoria": self.category,
            "grupo": self.muscle_group,
            "arquivo": self.filename,
            "nome_original": self.original_name,
            "nome_normalizado": self.normalized_name,
            "extensao": self.extension,
            "tamanho": self.size,
            "caminho": str(self.path),
        }


@dataclass(frozen=True, slots=True)
class MediaInventory:
    root: Path
    assets: tuple[MediaAsset, ...]

    def __iter__(self) -> Iterator[MediaAsset]:
        return iter(self.assets)

    def __len__(self) -> int:
        return len(self.assets)

    def to_records(self) -> list[dict[str, object]]:
        return [asset.to_dict() for asset in self.assets]

    def save_json(self, destination: str | Path) -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_records(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return target


def save_inventory(inventory: MediaInventory | Iterable[MediaAsset] | Iterable[dict], destination: str | Path) -> Path:
    """Persiste inventários novos ou a lista de dicionários usada legadamente."""
    if isinstance(inventory, MediaInventory):
        return inventory.save_json(destination)
    records = [item.to_dict() if isinstance(item, MediaAsset) else item for item in inventory]
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


salvar_inventario = save_inventory
