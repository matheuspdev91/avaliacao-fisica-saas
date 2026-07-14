"""Ponto de extensão para upload futuro; intencionalmente sem I/O nesta etapa."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class MediaUploader(Protocol):
    def upload(self, path: Path) -> str:
        """Deverá devolver a URL pública da mídia enviada."""
