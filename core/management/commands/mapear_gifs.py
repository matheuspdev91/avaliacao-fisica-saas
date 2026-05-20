"""
Management command: mapear_gifs
================================
Escaneia o diretório de GIFs físicos e preenche VariacaoExercicio.gif no banco.

USO
---
# 1. Análise (sem alterar nada):
python manage.py mapear_gifs

# 2. Análise com diretório customizado:
python manage.py mapear_gifs --path media/exercicios/gif

# 3. Aplicar apenas os matches automáticos confirmados:
python manage.py mapear_gifs --apply

# 4. Aplicar + forçar repath (quando o upload_to do model mudou):
python manage.py mapear_gifs --apply --prefix exercicios/gif

LÓGICA DE MATCHING
------------------
Normaliza tanto o nome do arquivo quanto o nome da variação/exercício:
  - lowercase
  - remove acentos
  - troca espaços, hífens, parênteses por underscore
  - remove tokens curtos (de, da, do, e, a, o)

Tenta matches nesta ordem de prioridade:
  1. Exact match:   nome_arquivo == variacao_normalizada
  2. Combo match:   nome_arquivo contém exercicio + variacao normalizados
  3. Partial match: nome_arquivo contém variacao normalizada (avisa ambiguidade)

Nunca escreve sem --apply. Nunca sobrescreve campo já preenchido sem --overwrite.
"""

import os
import re
import unicodedata
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import VariacaoExercicio


# ---------------------------------------------------------------------------
# Helpers de normalização
# ---------------------------------------------------------------------------

_STOP_WORDS = {"de", "da", "do", "dos", "das", "e", "a", "o", "em", "no", "na"}


def _normalizar(texto: str) -> str:
    """Lowercase, sem acentos, sem pontuação, tokens limpos."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def _tokens(normalizado: str) -> set:
    return {t for t in normalizado.split("_") if t not in _STOP_WORDS and len(t) > 1}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Escaneia o diretório de GIFs e mapeia para VariacaoExercicio.gif"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help=(
                "Caminho relativo à BASE_DIR onde os GIFs estão. "
                "Padrão: media/exercicios/gif"
            ),
        )
        parser.add_argument(
            "--prefix",
            default=None,
            help=(
                "Prefixo relativo ao MEDIA_ROOT gravado no campo .gif. "
                "Padrão: detectado automaticamente a partir de --path."
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Executa os writes no banco. Sem esta flag, apenas analisa.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Sobrescreve registros que já possuem .gif preenchido.",
        )

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        apply   = options["apply"]
        overwrite = options["overwrite"]

        # --- Resolve diretório físico ---
        base_dir   = Path(settings.BASE_DIR)
        media_root = Path(settings.MEDIA_ROOT)

        if options["path"]:
            gif_dir = Path(options["path"])
            if not gif_dir.is_absolute():
                gif_dir = base_dir / gif_dir
        else:
            gif_dir = base_dir / "media" / "exercicios" / "gif"

        if not gif_dir.exists():
            raise CommandError(
                f"Diretório não encontrado: {gif_dir}\n"
                f"Use --path para especificar o caminho correto."
            )

        # --- Resolve prefixo relativo ao MEDIA_ROOT (salvo no campo .gif) ---
        if options["prefix"]:
            prefix = options["prefix"].strip("/")
        else:
            try:
                prefix = str(gif_dir.relative_to(media_root)).replace("\\", "/")
            except ValueError:
                # gif_dir está fora do MEDIA_ROOT — usa caminho absoluto e avisa
                prefix = None
                self.stderr.write(
                    self.style.WARNING(
                        f"\nAVISO: {gif_dir} está fora do MEDIA_ROOT ({media_root}).\n"
                        f"Use --prefix para definir o prefixo relativo salvo no banco.\n"
                        f"Exemplo: --prefix exercicios/gif\n"
                    )
                )

        # --- Escaneia arquivos ---
        extensoes_validas = {".gif", ".mp4", ".webp", ".png", ".jpg", ".jpeg"}
        arquivos = sorted(
            f for f in gif_dir.iterdir()
            if f.is_file() and f.suffix.lower() in extensoes_validas
        )

        if not arquivos:
            self.stderr.write(self.style.WARNING(f"Nenhum arquivo de mídia encontrado em {gif_dir}"))
            return

        self.stdout.write(f"\nEncontrados {len(arquivos)} arquivo(s) em:\n  {gif_dir}\n")

        # --- Carrega variações do banco ---
        variacoes = list(
            VariacaoExercicio.objects.select_related("exercicio").all()
        )

        # Pré-computa tokens normalizados para cada variação
        variacao_map = []
        for v in variacoes:
            norm_variacao  = _normalizar(v.nome)
            norm_exercicio = _normalizar(v.exercicio.nome)
            combo          = f"{norm_exercicio}_{norm_variacao}"
            variacao_map.append({
                "obj":           v,
                "norm_variacao": norm_variacao,
                "norm_exercicio": norm_exercicio,
                "combo":         combo,
                "tokens_variacao":  _tokens(norm_variacao),
                "tokens_exercicio": _tokens(norm_exercicio),
                "tokens_combo":     _tokens(combo),
            })

        # --- Matching ---
        resultados = []   # (arquivo, match_obj | None, confiança, nota)

        for arquivo in arquivos:
            stem = _normalizar(arquivo.stem)   # nome sem extensão, normalizado
            tokens_arquivo = _tokens(stem)

            candidatos = []

            for vm in variacao_map:
                # Prioridade 1 — exact no combo "exercicio_variacao"
                if stem == vm["combo"]:
                    candidatos.append((vm["obj"], "exact-combo", 100))
                    continue

                # Prioridade 2 — exact na variação isolada
                if stem == vm["norm_variacao"]:
                    candidatos.append((vm["obj"], "exact-variacao", 90))
                    continue

                # Prioridade 3 — todos os tokens do combo estão no arquivo
                if vm["tokens_combo"] and vm["tokens_combo"].issubset(tokens_arquivo):
                    candidatos.append((vm["obj"], "tokens-combo", 70))
                    continue

                # Prioridade 4 — tokens da variação contidos no arquivo
                if vm["tokens_variacao"] and vm["tokens_variacao"].issubset(tokens_arquivo):
                    # Verifica também se o exercício aparece para reduzir falsos positivos
                    ex_intersect = vm["tokens_exercicio"].intersection(tokens_arquivo)
                    score = 60 if ex_intersect else 40
                    candidatos.append((vm["obj"], "tokens-variacao", score))

            if not candidatos:
                resultados.append((arquivo, None, 0, "SEM MATCH"))
                continue

            # Ordena por score desc, pega o melhor
            candidatos.sort(key=lambda x: x[2], reverse=True)
            melhor_obj, melhor_tipo, melhor_score = candidatos[0]

            # Ambiguidade: mais de um candidato com mesmo score máximo
            empates = [c for c in candidatos if c[2] == melhor_score]
            if len(empates) > 1:
                nota = f"AMBÍGUO ({len(empates)} candidatos, score={melhor_score})"
                resultados.append((arquivo, None, melhor_score, nota))
            else:
                resultados.append((arquivo, melhor_obj, melhor_score, melhor_tipo))

        # --- Relatório ---
        self._imprimir_relatorio(resultados, prefix, overwrite)

        # --- Apply ---
        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "\nMODO ANÁLISE — nenhum registro foi alterado.\n"
                    "Use --apply para persistir os matches no banco.\n"
                )
            )
            return

        if prefix is None:
            raise CommandError(
                "Não foi possível determinar o prefixo relativo ao MEDIA_ROOT.\n"
                "Use --prefix para especificar. Ex: --prefix exercicios/gif"
            )

        atualizados  = 0
        ignorados    = 0
        sem_match    = 0

        for arquivo, variacao_obj, score, nota in resultados:
            if variacao_obj is None:
                sem_match += 1
                continue

            if variacao_obj.gif and not overwrite:
                ignorados += 1
                continue

            caminho_relativo = f"{prefix}/{arquivo.name}"
            variacao_obj.gif = caminho_relativo
            variacao_obj.save(update_fields=["gif"])
            atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Concluído — {atualizados} atualizado(s), "
                f"{ignorados} já preenchido(s) ignorado(s), "
                f"{sem_match} sem match.\n"
            )
        )

    # ------------------------------------------------------------------

    def _imprimir_relatorio(self, resultados, prefix, overwrite):
        self.stdout.write("\n" + "─" * 82)
        self.stdout.write(
            f"{'ARQUIVO':<35} {'VARIAÇÃO ENCONTRADA':<30} {'SCORE':>5}  {'STATUS'}"
        )
        self.stdout.write("─" * 82)

        for arquivo, variacao_obj, score, nota in resultados:
            nome_arquivo = arquivo.name[:34]

            if variacao_obj is None:
                variacao_str = "—"
                status = self.style.ERROR(nota)
            else:
                variacao_str = f"{variacao_obj.exercicio.nome} / {variacao_obj.nome}"
                variacao_str = variacao_str[:29]

                ja_tem_gif = bool(variacao_obj.gif)
                if ja_tem_gif and not overwrite:
                    status = self.style.WARNING("JÁ PREENCHIDO (pular)")
                else:
                    status = self.style.SUCCESS(f"OK → {nota}")

            self.stdout.write(
                f"{nome_arquivo:<35} {variacao_str:<30} {score:>5}  {status}"
            )

        # Sumário
        total      = len(resultados)
        com_match  = sum(1 for _, v, _, _ in resultados if v)
        sem_match  = total - com_match
        ja_cheios  = sum(1 for _, v, _, _ in resultados if v and v.gif)

        self.stdout.write("─" * 82)
        self.stdout.write(
            f"Total: {total} arquivo(s) | "
            f"Com match: {com_match} | "
            f"Sem match: {sem_match} | "
            f"Já preenchidos no banco: {ja_cheios}"
        )
        self.stdout.write("─" * 82 + "\n")

        if prefix:
            self.stdout.write(f"Prefixo que será salvo no banco: {prefix}/<arquivo>\n")
