#!/usr/bin/env python3
"""Aplica GIFs mapeados no relatório de auditoria ao Cloudinary e ao banco.

Lê audit_gifs_orfaos.csv (gerado por corrigir_gifs_orfaos.py), processa
somente registros com status=MATCH, faz upload do arquivo local para o
Cloudinary e salva a secure_url retornada no campo VariacaoExercicio.gif.

Registros com status VALIDO, AMBIGUO ou SEM_MATCH são ignorados.

MODO DRY RUN (padrão):
    Simula todo o fluxo sem fazer upload nem alterar o banco.
    Gera o log CSV normalmente com status DRY_RUN.

    python aplicar_gifs_match.py

MODO REAL:
    python aplicar_gifs_match.py --no-dry-run

OPÇÕES:
    --csv         Caminho do CSV de entrada  (padrão: audit_gifs_orfaos.csv)
    --log         Caminho do CSV de log      (padrão: log_aplicar_gifs.csv)
    --no-dry-run  Executa de verdade (upload + banco)
    --ids         Lista de IDs para processar (ex.: --ids 863 864 870)
                  Útil para testar uma amostra antes do lote completo.
    --score-min   Score mínimo para processar (padrão: 0.0, aceita tudo)

Fluxo por registro:
    1. Valida que o arquivo local existe.
    2. Faz upload para o Cloudinary com public_id determinístico.
    3. Salva a secure_url no banco via .save(update_fields=["gif"]).
    4. Registra resultado (SUCESSO ou ERRO) no log CSV.

Em caso de erro em qualquer etapa, o registro é marcado como ERRO no log
e o script continua para o próximo — sem interromper o lote.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

import django
from django.conf import settings


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

# Public ID base no Cloudinary. O sufixo será o ID da variação.
# Exemplo: exercicios/gif/variacao-863
CLOUDINARY_FOLDER = "exercicios/gif"
PUBLIC_ID_TEMPLATE = "variacao-{variacao_id}"

# Campos do CSV de entrada (devem bater com o gerado por corrigir_gifs_orfaos.py)
CSV_IN_FIELDS = ["id", "variacao_nome", "exercicio", "cloudinary_atual",
                 "status", "arquivo_gif", "score", "observacao"]

# Campos do CSV de log de saída
LOG_FIELDS = ["id", "variacao_nome", "exercicio", "arquivo_gif",
              "score", "resultado", "url_salva", "detalhe", "timestamp"]

STATUS_MATCH = "MATCH"


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class CsvRecord:
    variacao_id: int
    variacao_nome: str
    exercicio: str
    cloudinary_atual: str
    status: str
    arquivo_gif: str        # caminho relativo ao gif_root
    score: float
    observacao: str


@dataclass
class LogRow:
    variacao_id: int
    variacao_nome: str
    exercicio: str
    arquivo_gif: str
    score: float
    resultado: str          # SUCESSO / ERRO / DRY_RUN / IGNORADO
    url_salva: str = ""
    detalhe: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


# ---------------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------------

def setup_django_environment() -> None:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projeto.settings")
    django.setup()


# ---------------------------------------------------------------------------
# Leitura do CSV de entrada
# ---------------------------------------------------------------------------

def load_csv(csv_path: Path) -> List[CsvRecord]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV de entrada não encontrado: {csv_path}")

    records: List[CsvRecord] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                records.append(CsvRecord(
                    variacao_id=int(row["id"]),
                    variacao_nome=row["variacao_nome"],
                    exercicio=row["exercicio"],
                    cloudinary_atual=row.get("cloudinary_atual", ""),
                    status=row["status"],
                    arquivo_gif=row.get("arquivo_gif", ""),
                    score=float(row["score"]) if row.get("score") else 0.0,
                    observacao=row.get("observacao", ""),
                ))
            except (ValueError, KeyError) as e:
                print(f"[AVISO] Linha ignorada por erro de leitura: {row} — {e}")
    return records


# ---------------------------------------------------------------------------
# Saída CSV de log
# ---------------------------------------------------------------------------

def write_log(rows: List[LogRow], log_path: Path) -> None:
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row.variacao_id,
                "variacao_nome": row.variacao_nome,
                "exercicio": row.exercicio,
                "arquivo_gif": row.arquivo_gif,
                "score": f"{row.score:.4f}" if row.score else "",
                "resultado": row.resultado,
                "url_salva": row.url_salva,
                "detalhe": row.detalhe,
                "timestamp": row.timestamp,
            })


# ---------------------------------------------------------------------------
# Upload para o Cloudinary
# ---------------------------------------------------------------------------

def upload_to_cloudinary(local_path: Path, variacao_id: int) -> str:
    """
    Faz upload do arquivo GIF para o Cloudinary.

    Retorna a secure_url do recurso criado.

    Usa public_id determinístico (variacao-{id}) para ser idempotente:
    re-executar o script no mesmo ID sobrescreve o upload anterior,
    sem criar duplicatas no Cloudinary.
    """
    import cloudinary
    import cloudinary.uploader

    public_id = f"{CLOUDINARY_FOLDER}/{PUBLIC_ID_TEMPLATE.format(variacao_id=variacao_id)}"

    result = cloudinary.uploader.upload(
        str(local_path),
        public_id=public_id,
        resource_type="image",   # GIFs são tratados como image no Cloudinary
        overwrite=True,
        invalidate=True,         # Invalida CDN cache se já existia
    )

    secure_url = result.get("secure_url")
    if not secure_url:
        raise ValueError(f"Upload concluído mas secure_url ausente na resposta: {result}")

    return secure_url


# ---------------------------------------------------------------------------
# Atualização no banco
# ---------------------------------------------------------------------------

def save_url_to_db(variacao_id: int, secure_url: str) -> None:
    """
    Salva a secure_url no campo gif da VariacaoExercicio.

    Usa update_fields para tocar apenas o campo gif e evitar
    side effects de signals que dependam de outros campos.
    """
    from core.models import VariacaoExercicio

    variacao = VariacaoExercicio.objects.get(pk=variacao_id)
    variacao.gif = secure_url
    variacao.save(update_fields=["gif"])


# ---------------------------------------------------------------------------
# Processamento principal
# ---------------------------------------------------------------------------

def process_records(
    records: List[CsvRecord],
    gif_root: Path,
    dry_run: bool,
    filter_ids: Optional[Set[int]],
    score_min: float,
) -> List[LogRow]:
    log_rows: List[LogRow] = []

    match_records = [r for r in records if r.status == STATUS_MATCH]
    total = len(match_records)

    if filter_ids:
        match_records = [r for r in match_records if r.variacao_id in filter_ids]
        print(f"Filtro por IDs aplicado: {len(match_records)} de {total} registros MATCH")

    if score_min > 0.0:
        before = len(match_records)
        match_records = [r for r in match_records if r.score >= score_min]
        print(f"Filtro por score >= {score_min}: {len(match_records)} de {before} registros")

    print(f"\nRegistros a processar: {len(match_records)}")
    print(f"Modo: {'DRY RUN (simulação)' if dry_run else '*** REAL — alterações serão salvas ***'}")
    print()

    counters = {"SUCESSO": 0, "ERRO": 0, "DRY_RUN": 0}

    for i, rec in enumerate(match_records, 1):
        prefix = f"[{i}/{len(match_records)}] ID {rec.variacao_id} | {rec.variacao_nome}"

        # Valida arquivo local
        local_path = gif_root / rec.arquivo_gif
        if not local_path.exists():
            msg = f"Arquivo local não encontrado: {local_path}"
            print(f"  [ERRO] {prefix}\n         {msg}")
            counters["ERRO"] += 1
            log_rows.append(LogRow(
                variacao_id=rec.variacao_id,
                variacao_nome=rec.variacao_nome,
                exercicio=rec.exercicio,
                arquivo_gif=rec.arquivo_gif,
                score=rec.score,
                resultado="ERRO",
                detalhe=msg,
            ))
            continue

        if dry_run:
            print(f"  [DRY RUN] {prefix}")
            print(f"            arquivo : {rec.arquivo_gif}")
            print(f"            score   : {rec.score:.4f}")
            counters["DRY_RUN"] += 1
            log_rows.append(LogRow(
                variacao_id=rec.variacao_id,
                variacao_nome=rec.variacao_nome,
                exercicio=rec.exercicio,
                arquivo_gif=rec.arquivo_gif,
                score=rec.score,
                resultado="DRY_RUN",
                detalhe="Simulação — nenhuma alteração realizada",
            ))
            continue

        # Modo real: upload + banco
        try:
            secure_url = upload_to_cloudinary(local_path, rec.variacao_id)
            save_url_to_db(rec.variacao_id, secure_url)

            print(f"  [OK] {prefix}")
            print(f"       url: {secure_url}")
            counters["SUCESSO"] += 1
            log_rows.append(LogRow(
                variacao_id=rec.variacao_id,
                variacao_nome=rec.variacao_nome,
                exercicio=rec.exercicio,
                arquivo_gif=rec.arquivo_gif,
                score=rec.score,
                resultado="SUCESSO",
                url_salva=secure_url,
            ))

        except Exception as e:
            detalhe = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"
            print(f"  [ERRO] {prefix}")
            print(f"         {type(e).__name__}: {e}")
            counters["ERRO"] += 1
            log_rows.append(LogRow(
                variacao_id=rec.variacao_id,
                variacao_nome=rec.variacao_nome,
                exercicio=rec.exercicio,
                arquivo_gif=rec.arquivo_gif,
                score=rec.score,
                resultado="ERRO",
                detalhe=detalhe,
            ))

    print()
    print("=" * 50)
    print("RESUMO")
    print("=" * 50)
    if dry_run:
        print(f"DRY RUN   : {counters['DRY_RUN']}")
    else:
        print(f"SUCESSO   : {counters['SUCESSO']}")
    print(f"ERRO      : {counters['ERRO']}")
    print(f"Total     : {len(match_records)}")

    return log_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aplica GIFs mapeados no CSV de auditoria ao Cloudinary e ao banco. "
            "DRY RUN por padrão — use --no-dry-run para executar de verdade."
        )
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("audit_gifs_orfaos.csv"),
        help="CSV de entrada gerado por corrigir_gifs_orfaos.py (padrão: audit_gifs_orfaos.csv)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("log_aplicar_gifs.csv"),
        help="CSV de log de saída (padrão: log_aplicar_gifs.csv)",
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="Executa de verdade: faz upload e salva no banco",
    )
    parser.add_argument(
        "--ids",
        type=int,
        nargs="+",
        metavar="ID",
        help="Processar apenas estes IDs (ex.: --ids 863 864 870)",
    )
    parser.add_argument(
        "--score-min",
        type=float,
        default=0.0,
        metavar="SCORE",
        help="Score mínimo para processar (ex.: --score-min 0.95)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    setup_django_environment()

    gif_root = Path(settings.MEDIA_ROOT) / "exercicios" / "gif"

    print(f"CSV entrada : {args.csv}")
    print(f"Log saída   : {args.log}")
    print(f"GIF root    : {gif_root}")

    records = load_csv(args.csv)

    total_no_csv = len(records)
    total_match = sum(1 for r in records if r.status == STATUS_MATCH)
    total_outros = total_no_csv - total_match

    print(f"Total no CSV: {total_no_csv}  |  MATCH: {total_match}  |  Outros (ignorados): {total_outros}")

    filter_ids: Optional[Set[int]] = set(args.ids) if args.ids else None

    log_rows = process_records(
        records=records,
        gif_root=gif_root,
        dry_run=args.dry_run,
        filter_ids=filter_ids,
        score_min=args.score_min,
    )

    write_log(log_rows, args.log)
    print(f"\nLog salvo em: {args.log}")


if __name__ == "__main__":
    main()
