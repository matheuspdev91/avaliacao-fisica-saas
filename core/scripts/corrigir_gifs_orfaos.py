#!/usr/bin/env python3
"""Corrige variações de exercício com GIFs órfãos ou inválidos no Cloudinary.

Este script encontra variações cujo campo `gif` está vazio ou inválido,
procura o arquivo GIF local correspondente em media/exercicios/gif/ e gera um
relatório de correspondências sem fazer upload, sem salvar no banco e sem
alterar registros.

Uso:
  python core/scripts/corrigir_gifs_orfaos.py

Somente relatório, sem alterações.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import django
from django.conf import settings


MATCH_THRESHOLD = 0.90
GIF_ROOT_RELATIVE = Path("media") / "exercicios" / "gif"


@dataclass
class MatchCandidate:
    variacao_id: int
    variacao_nome: str
    arquivo_path: Path
    score: float


def setup_django_environment() -> None:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projeto.settings")
    django.setup()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("utf-8")
    value = value.lower()
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_variacao_problematic(variacao) -> bool:
    try:
        resource = variacao.gif

        url = getattr(resource, "url", None)
        public_id = getattr(resource, "public_id", None)

        if not url:
            return True
        
        if not public_id:
            return True
        
        return False
    
    except Exception:
        # CLOUDINARY RESOURCE QUEBRADO
        return True



def find_gif_files(root: Path) -> List[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Diretório de GIFs não encontrado: {root}")
    return sorted(root.rglob("*.gif"))


def get_cloudinary_url(variacao) -> str:
    try:
        resource = variacao.gif
        
        url = getattr(resource, "url", None)
        return url or "Nenhum"
    
    except Exception:
        return "Inválido"
  


def match_score(source: str, candidate: str) -> float:
    source_norm = normalize_text(source)
    candidate_norm = normalize_text(candidate)
    if not source_norm or not candidate_norm:
        return 0.0
    return float(SequenceMatcher(None, source_norm, candidate_norm).ratio())


def find_best_match(variacao_nome: str, gif_files: Iterable[Path]) -> Tuple[Optional[Path], float]:
    candidates: List[Tuple[float, Path]] = []
    for path in gif_files:
        score = match_score(variacao_nome, path.stem)
        if score >= MATCH_THRESHOLD:
            candidates.append((score, path))

    if not candidates:
        return None, 0.0

    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    if len(candidates) > 1 and abs(candidates[0][0] - candidates[1][0]) < 1e-9:
        return None, candidates[0][0]

    return candidates[0][1], candidates[0][0]


def main() -> None:
    setup_django_environment()

    from core.models import VariacaoExercicio

    gif_root = Path(settings.MEDIA_ROOT) / "exercicios" / "gif"
    gif_files = find_gif_files(gif_root)

    variacoes = list(VariacaoExercicio.objects.select_related("exercicio").order_by("id"))

    matches: List[MatchCandidate] = []
    ignored = 0
    no_match = 0
    analyzed = len(variacoes)

    print(f"GIF root: {gif_root}")
    print(f"Variações encontradas: {len(variacoes)}")
    print(f"GIFs locais encontrados: {len(gif_files)}")
    print("\nAnalisando variações...\n")

    for variacao in variacoes:
        current_url = get_cloudinary_url(variacao)
        if not is_variacao_problematic(variacao):
            print("[SKIP]")
            print(f"ID: {variacao.pk}")
            print(f"Variacao: {variacao.nome}")
            print(f"Cloudinary atual: {current_url}\n")
            ignored += 1
            continue

        arquivo, score = find_best_match(variacao.nome, gif_files)
        if arquivo is None:
            print("[NO MATCH]")
            print(f"ID: {variacao.pk}")
            print(f"Variacao: {variacao.nome}")
            print("Arquivo encontrado: Nenhum")
            print(f"Score: {score:.2f}")
            print(f"Cloudinary atual: {current_url}\n")
            no_match += 1
            continue

        matches.append(MatchCandidate(variacao.pk, variacao.nome, arquivo, score))
        print("[MATCH]")
        print(f"ID: {variacao.pk}")
        print(f"Variacao: {variacao.nome}")
        print(f"Arquivo encontrado: {arquivo.relative_to(gif_root) if arquivo.is_relative_to(gif_root) else arquivo.name}")
        print(f"Score: {score:.2f}")
        print(f"Cloudinary atual: {current_url}\n")

    print("---\nResumo final:")
    print(f"Analisados: {analyzed}")
    print(f"Corrigíveis: {len(matches)}")
    print(f"Sem match: {no_match}")
    print(f"Ignorados: {ignored}")


if __name__ == "__main__":
    main()
