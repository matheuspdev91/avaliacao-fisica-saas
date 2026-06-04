#!/usr/bin/env python3
"""Auditoria de variações com GIFs órfãos ou inválidos no Cloudinary.

Gera um relatório CSV com correspondências entre variações problemáticas e
arquivos GIF locais encontrados em media/exercicios/gif/.

NÃO faz upload para o Cloudinary.
NÃO salva no banco de dados.
NÃO altera nenhum registro.

Uso:
    python corrigir_gifs_orfaos.py [--output CAMINHO.csv]

Saída padrão: audit_gifs_orfaos.csv (no diretório de execução)
"""

from __future__ import annotations

import argparse
import csv
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


# ---------------------------------------------------------------------------
# Configuração de matching
# ---------------------------------------------------------------------------

# Limiar primário: score mínimo do SequenceMatcher para aceitar um candidato.
MATCH_THRESHOLD = 0.85  # Reduzido de 0.90 — ver nota sobre falsos positivos abaixo.

# Limiar de desambiguação: diferença mínima entre o melhor e o segundo melhor
# candidato para considerar o match seguro. Abaixo disso → AMBÍGUO.
AMBIGUITY_GAP = 0.05

# Penalidade aplicada quando o candidato tem palavras extras relevantes
# que não existem na variação (ex.: "Com Barra" vs "Com Cabo").
# Isso resolve falsos positivos entre variações próximas.
EXTRA_WORD_PENALTY = 0.08


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class AuditRow:
    variacao_id: int
    variacao_nome: str
    exercicio_nome: str
    cloudinary_atual: str
    status: str           # VALIDO / MATCH / AMBIGUO / SEM_MATCH
    arquivo_gif: str      # caminho relativo ou vazio
    score: float
    observacao: str       # detalhe adicional para revisão manual


# ---------------------------------------------------------------------------
# Inicialização do Django
# ---------------------------------------------------------------------------

def setup_django_environment() -> None:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projeto.settings")
    django.setup()


# ---------------------------------------------------------------------------
# Normalização de texto
# ---------------------------------------------------------------------------

def normalize_text(value: str) -> str:
    """Remove acentos, pontuação, caixa e normaliza espaços."""
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("utf-8")
    value = value.lower()
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def word_set(text: str) -> set:
    """Retorna conjunto de palavras normalizadas."""
    return set(normalize_text(text).split())


# ---------------------------------------------------------------------------
# Score composto (SequenceMatcher + penalidade por palavras extras)
# ---------------------------------------------------------------------------

def compute_score(variacao_nome: str, candidate_stem: str) -> float:
    """
    Calcula score composto entre o nome da variação e o stem do arquivo GIF.

    O score base usa SequenceMatcher (sensível à ordem dos caracteres).
    Uma penalidade é aplicada quando o candidato possui palavras significativas
    que não aparecem no nome da variação — isso reduz falsos positivos entre
    nomes parecidos mas com equipamentos diferentes (ex.: Barra vs Cabo).

    Palavras funcionais (stopwords) não são penalizadas.
    """
    STOPWORDS = {"com", "de", "da", "do", "em", "na", "no", "e", "a", "o",
                 "um", "uma", "para", "por", "se", "ao", "as", "os"}

    norm_variacao = normalize_text(variacao_nome)
    norm_candidate = normalize_text(candidate_stem)

    if not norm_variacao or not norm_candidate:
        return 0.0

    base_score = float(SequenceMatcher(None, norm_variacao, norm_candidate).ratio())

    # Palavras do candidato que não estão na variação e não são stopwords
    words_variacao = word_set(variacao_nome)
    words_candidate = word_set(candidate_stem)
    extra_words = (words_candidate - words_variacao) - STOPWORDS

    # Cada palavra extra relevante penaliza o score
    penalty = len(extra_words) * EXTRA_WORD_PENALTY
    adjusted_score = max(0.0, base_score - penalty)

    return adjusted_score


# ---------------------------------------------------------------------------
# Validação de registro no Cloudinary
# ---------------------------------------------------------------------------

def get_cloudinary_status(variacao) -> Tuple[bool, str]:
    """
    Retorna (is_problematic, url_atual).

    Lê o valor bruto do banco (evita depender do comportamento do SDK
    para construir URLs a partir de public_id vazio).
    """
    from core.models import VariacaoExercicio

    try:
        raw_value = (
            VariacaoExercicio.objects
            .filter(id=variacao.id)
            .values_list("gif", flat=True)
            .first()
        )
    except Exception as e:
        return True, f"ERRO_DB: {e}"

    if not raw_value:
        return True, ""

    # Valor bruto pode ser URL completa ou public_id do Cloudinary
    raw_str = str(raw_value).strip()
    if not raw_str:
        return True, ""

    # Registro considerado válido se tiver qualquer valor não-vazio no campo
    return False, raw_str


# ---------------------------------------------------------------------------
# Descoberta de arquivos GIF
# ---------------------------------------------------------------------------

def find_gif_files(root: Path) -> List[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Diretório de GIFs não encontrado: {root}")
    return sorted(root.rglob("*.gif"))


# ---------------------------------------------------------------------------
# Matching principal
# ---------------------------------------------------------------------------

def find_best_match(
    variacao_nome: str,
    gif_files: Iterable[Path],
) -> Tuple[Optional[Path], float, str]:
    """
    Retorna (melhor_arquivo, score, observacao).

    observacao pode indicar ambiguidade para revisão manual.
    """
    candidates: List[Tuple[float, Path]] = []

    for path in gif_files:
        score = compute_score(variacao_nome, path.stem)
        if score >= MATCH_THRESHOLD:
            candidates.append((score, path))

    if not candidates:
        return None, 0.0, ""

    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    best_score, best_path = candidates[0]

    if len(candidates) > 1:
        gap = best_score - candidates[1][0]
        if gap < AMBIGUITY_GAP:
            obs = (
                f"AMBÍGUO: melhor={best_path.stem}({best_score:.3f}), "
                f"segundo={candidates[1][1].stem}({candidates[1][0]:.3f}), "
                f"gap={gap:.3f}"
            )
            # Retorna None para forçar revisão manual — não arrisca match errado
            return None, best_score, obs

    return best_path, best_score, ""


# ---------------------------------------------------------------------------
# Saída CSV
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "id",
    "variacao_nome",
    "exercicio",
    "cloudinary_atual",
    "status",
    "arquivo_gif",
    "score",
    "observacao",
]


def write_csv(rows: List[AuditRow], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row.variacao_id,
                "variacao_nome": row.variacao_nome,
                "exercicio": row.exercicio_nome,
                "cloudinary_atual": row.cloudinary_atual,
                "status": row.status,
                "arquivo_gif": row.arquivo_gif,
                "score": f"{row.score:.4f}" if row.score else "",
                "observacao": row.observacao,
            })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auditoria de GIFs órfãos — somente relatório, sem alterações."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit_gifs_orfaos.csv"),
        help="Caminho do arquivo CSV de saída (padrão: audit_gifs_orfaos.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_django_environment()

    from core.models import VariacaoExercicio

    gif_root = Path(settings.MEDIA_ROOT) / "exercicios" / "gif"
    gif_files = find_gif_files(gif_root)

    variacoes = list(
        VariacaoExercicio.objects.select_related("exercicio").order_by("id")
    )

    print(f"GIF root        : {gif_root}")
    print(f"Variações       : {len(variacoes)}")
    print(f"GIFs locais     : {len(gif_files)}")
    print(f"Saída CSV       : {args.output}")
    print()

    rows: List[AuditRow] = []

    counters = {
        "VALIDO": 0,
        "MATCH": 0,
        "AMBIGUO": 0,
        "SEM_MATCH": 0,
    }

    for variacao in variacoes:
        is_problematic, cloudinary_atual = get_cloudinary_status(variacao)

        exercicio_nome = ""
        try:
            exercicio_nome = variacao.exercicio.nome if variacao.exercicio else ""
        except Exception:
            pass

        if not is_problematic:
            counters["VALIDO"] += 1
            rows.append(AuditRow(
                variacao_id=variacao.pk,
                variacao_nome=variacao.nome,
                exercicio_nome=exercicio_nome,
                cloudinary_atual=cloudinary_atual,
                status="VALIDO",
                arquivo_gif="",
                score=0.0,
                observacao="",
            ))
            continue

        arquivo, score, obs = find_best_match(variacao.nome, gif_files)

        if obs:
            # Ambiguidade: não decide automaticamente
            status = "AMBIGUO"
            counters["AMBIGUO"] += 1
            rows.append(AuditRow(
                variacao_id=variacao.pk,
                variacao_nome=variacao.nome,
                exercicio_nome=exercicio_nome,
                cloudinary_atual=cloudinary_atual,
                status=status,
                arquivo_gif="",
                score=score,
                observacao=obs,
            ))
            continue

        if arquivo is None:
            status = "SEM_MATCH"
            counters["SEM_MATCH"] += 1
            rows.append(AuditRow(
                variacao_id=variacao.pk,
                variacao_nome=variacao.nome,
                exercicio_nome=exercicio_nome,
                cloudinary_atual=cloudinary_atual,
                status=status,
                arquivo_gif="",
                score=score,
                observacao="",
            ))
            continue

        status = "MATCH"
        counters["MATCH"] += 1
        arquivo_rel = (
            str(arquivo.relative_to(gif_root))
            if arquivo.is_relative_to(gif_root)
            else arquivo.name
        )
        rows.append(AuditRow(
            variacao_id=variacao.pk,
            variacao_nome=variacao.nome,
            exercicio_nome=exercicio_nome,
            cloudinary_atual=cloudinary_atual,
            status=status,
            arquivo_gif=arquivo_rel,
            score=score,
            observacao="",
        ))

    write_csv(rows, args.output)

    print("=" * 50)
    print("RESUMO FINAL")
    print("=" * 50)
    print(f"Total analisado : {len(variacoes)}")
    print(f"VALIDO          : {counters['VALIDO']}")
    print(f"MATCH           : {counters['MATCH']}")
    print(f"AMBIGUO         : {counters['AMBIGUO']}  ← revisar manualmente")
    print(f"SEM_MATCH       : {counters['SEM_MATCH']}")
    print(f"\nRelatório salvo : {args.output}")


if __name__ == "__main__":
    main()
