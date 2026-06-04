#!/usr/bin/env python3

import csv
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher

INPUT_CSV = "variacoes_sem_gif.csv"
OUTPUT_CSV = "segunda_passagem.csv"

GIF_ROOT = Path("media/exercicios/gif")

MATCH_THRESHOLD = 0.85


def normalize(text):
    text = str(text).lower()

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")

    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b)
    ).ratio()


print("Carregando GIFs...")

gifs = list(GIF_ROOT.rglob("*.gif"))

print(f"GIFs encontrados: {len(gifs)}")

resultado = []

with open(INPUT_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:

        exercicio = row["exercicio"]
        variacao = row["variacao"]

        busca = f"{exercicio} {variacao}"

        melhor_score = 0
        melhor_arquivo = ""

        for gif in gifs:

            score = similarity(
                busca,
                gif.stem
            )

            if score > melhor_score:
                melhor_score = score
                melhor_arquivo = str(
                    gif.relative_to(GIF_ROOT)
                )

        status = (
            "MATCH"
            if melhor_score >= MATCH_THRESHOLD
            else "SEM_MATCH"
        )

        resultado.append({
            "id": row["id"],
            "exercicio": exercicio,
            "variacao": variacao,
            "busca": busca,
            "arquivo": melhor_arquivo,
            "score": round(melhor_score, 4),
            "status": status,
        })

with open(
    OUTPUT_CSV,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "id",
            "exercicio",
            "variacao",
            "busca",
            "arquivo",
            "score",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(resultado)

matches = sum(
    1 for r in resultado
    if r["status"] == "MATCH"
)

sem_match = sum(
    1 for r in resultado
    if r["status"] == "SEM_MATCH"
)

print()
print("=" * 60)
print("RESUMO")
print("=" * 60)
print(f"Total analisado : {len(resultado)}")
print(f"MATCH           : {matches}")
print(f"SEM_MATCH       : {sem_match}")
print()
print(f"CSV gerado: {OUTPUT_CSV}")