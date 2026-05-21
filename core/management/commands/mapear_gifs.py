"""
Management command: mapear_gifs_v2
===================================
Mapeia automaticamente GIFs físicos para VariacaoExercicio.gif usando
normalização agressiva e múltiplas estratégias de matching.

Criado para resolver os 59 registros que o mapear_gifs.py não conseguiu
mapear devido a diferenças de ordem, acentos, pontuação e caracteres especiais.

USO
---
# Preview (zero writes, padrão):
python manage.py mapear_gifs_v2

# Preview explícito:
python manage.py mapear_gifs_v2 --preview

# Aplicar apenas matches com score >= 90:
python manage.py mapear_gifs_v2 --apply

# Diretório customizado:
python manage.py mapear_gifs_v2 --path media/exercicios/gif

# Forçar prefixo salvo no banco:
python manage.py mapear_gifs_v2 --apply --prefix exercicios/gif

# Incluir variações que já têm gif (para auditoria):
python manage.py mapear_gifs_v2 --preview --all

ESTRATÉGIA DE MATCHING (em ordem de prioridade)
-------------------------------------------------
1. EXACT (score 100):
   normalizar(exercicio.nome + variacao.nome) == normalizar(arquivo)

2. EXACT_REVERSED (score 95):
   normalizar(variacao.nome + exercicio.nome) == normalizar(arquivo)

3. CONTAINS_FULL (score 85):
   normalizar(arquivo) contém normalizar(exercicio + variacao)
   OU normalizar(exercicio + variacao) contém normalizar(arquivo)

4. CONTAINS_REVERSED (score 80):
   idem mas com variacao + exercicio

5. SIMILARITY (score variável 50–89):
   difflib.SequenceMatcher entre variação normalizada e arquivo normalizado
   Só aceito como candidato se ratio >= 0.75

Regras de aplicação:
  score >= 90  → aplica automaticamente com --apply
  score 50–89  → sugere, NÃO aplica (requer intervenção manual)
  ambiguidade  → NÃO aplica (mais de um candidato com mesmo score máximo)
"""

import difflib
import re
import unicodedata
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import VariacaoExercicio

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

EXTENSOES = {".gif", ".mp4", ".webp", ".png", ".jpg", ".jpeg"}
SCORE_AUTO_APPLY = 70      # score mínimo para write automático
SCORE_MIN_REPORT = 50      # score mínimo para aparecer no relatório como candidato
SIMILARITY_MIN   = 0.75    # ratio mínimo do SequenceMatcher para entrar como candidato


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """
    Normalização agressiva:
      1. Remove acentos (NFKD decomposition)
      2. Converte para lowercase
      3. Remove TUDO que não seja letra ou dígito
    Resultado: string compacta sem separadores.

    Exemplos:
      "Supino Reto Barra"   → "supinoretobarra"
      "supino_reto_barra"   → "supinoretobarra"
      "Rosca 45°"           → "rosca45"
      "Agachamento (livre)" → "agachamentolivre"
      "T-Bar Row"           → "tbarrow"
    """
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]", "", texto)
    return texto


def normalizar_stem(path: Path) -> str:
    """Normaliza apenas o stem (nome sem extensão) de um Path."""
    return normalizar(path.stem)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_match(norm_arquivo: str, norm_combo: str, norm_combo_rev: str) -> tuple[int, str]:
    """
    Retorna (score, estratégia) para o par arquivo × variação.

    norm_arquivo   : normalizar(arquivo.stem)
    norm_combo     : normalizar(exercicio.nome + variacao.nome)
    norm_combo_rev : normalizar(variacao.nome + exercicio.nome)
    """

    # 1. Exact direto
    if norm_arquivo == norm_combo:
        return 100, "EXACT"

    # 2. Exact invertido
    if norm_arquivo == norm_combo_rev:
        return 95, "EXACT_REVERSED"

    # 3. Contains direto (arquivo contém combo OU combo contém arquivo)
    if norm_combo and (norm_combo in norm_arquivo or norm_arquivo in norm_combo):
        return 85, "CONTAINS"

    # 4. Contains invertido
    if norm_combo_rev and (norm_combo_rev in norm_arquivo or norm_arquivo in norm_combo_rev):
        return 80, "CONTAINS_REVERSED"

    # 5. Similarity — usa o maior dos dois combos como referência
    best_ratio = 0.0
    for ref in (norm_combo, norm_combo_rev):
        if not ref:
            continue
        ratio = difflib.SequenceMatcher(None, norm_arquivo, ref).ratio()
        if ratio > best_ratio:
            best_ratio = ratio

    if best_ratio >= SIMILARITY_MIN:
        # Mapeia ratio [0.75, 1.0] → score [50, 89]
        score = int(50 + (best_ratio - SIMILARITY_MIN) / (1.0 - SIMILARITY_MIN) * 39)
        return score, f"SIMILARITY({best_ratio:.2f})"

    return 0, "NO_MATCH"


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Mapeia GIFs físicos para VariacaoExercicio.gif com normalização agressiva. "
        "Use --apply para persistir. Sem a flag, apenas analisa (preview)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            metavar="DIR",
            help=(
                "Caminho (relativo à BASE_DIR ou absoluto) onde os GIFs estão. "
                "Padrão: media/exercicios/gif"
            ),
        )
        parser.add_argument(
            "--prefix",
            default=None,
            metavar="PREFIX",
            help=(
                "Prefixo relativo ao MEDIA_ROOT gravado no campo .gif. "
                "Padrão: detectado automaticamente a partir de --path. "
                "Exemplo: exercicios/gif"
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help=f"Persiste no banco os matches com score >= {SCORE_AUTO_APPLY}.",
        )
        parser.add_argument(
            "--preview",
            action="store_true",
            default=False,
            help="Força modo análise mesmo que --apply seja passado (override de segurança).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Inclui no relatório variações que já possuem gif (para auditoria).",
        )

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        apply_mode = options["apply"] and not options["preview"]

        # --- Resolve diretório físico ---
        base_dir   = Path(settings.BASE_DIR)
        media_root = Path(settings.MEDIA_ROOT)

        raw_path = options["path"] or "media/exercicios/gif"
        gif_dir  = Path(raw_path)
        if not gif_dir.is_absolute():
            gif_dir = base_dir / gif_dir

        if not gif_dir.exists():
            raise CommandError(
                f"\nDiretório não encontrado: {gif_dir}\n"
                f"Use --path para especificar o caminho correto.\n"
                f"Exemplo: --path media/exercicios/gif"
            )

        # --- Resolve prefixo relativo ao MEDIA_ROOT ---
        if options["prefix"]:
            prefix = options["prefix"].strip("/")
        else:
            try:
                prefix = str(gif_dir.relative_to(media_root)).replace("\\", "/")
            except ValueError:
                prefix = None

        # --- Carrega arquivos físicos ---
        arquivos = sorted(
            f for f in gif_dir.iterdir()
            if f.is_file() and f.suffix.lower() in EXTENSOES
        )

        if not arquivos:
            self.stderr.write(
                self.style.WARNING(f"Nenhum arquivo de mídia em: {gif_dir}")
            )
            return

        # --- Carrega variações ---
        qs = VariacaoExercicio.objects.select_related("exercicio").all()
        if not options["all"]:
            qs = qs.filter(gif="")   # apenas as sem gif

        variacoes = list(qs)

        # Pré-computa normalizações
        variacao_index = []
        for v in variacoes:
            nc  = normalizar(v.exercicio.nome + v.nome)
            ncr = normalizar(v.nome + v.exercicio.nome)
            variacao_index.append({
                "obj":   v,
                "combo": nc,
                "rev":   ncr,
            })

        # --- Executa matching ---
        # Para cada arquivo, encontra o melhor match entre as variações
        # Para cada variação, queremos no máximo 1 arquivo (o de maior score)
        # Resultado: lista de (arquivo, variacao_obj|None, score, estrategia, nota)

        resultados = []          # (arquivo, variacao_obj|None, score, estrategia)
        variacoes_usadas = {}    # variacao.id → (arquivo, score) para detectar conflitos

        for arquivo in arquivos:
            norm_arq = normalizar_stem(arquivo)
            candidatos = []   # (score, estrategia, variacao_dict)

            for vm in variacao_index:
                score, estrategia = score_match(norm_arq, vm["combo"], vm["rev"])
                if score >= SCORE_MIN_REPORT:
                    candidatos.append((score, estrategia, vm))

            if not candidatos:
                resultados.append((arquivo, None, 0, "NO_MATCH", ""))
                continue

            candidatos.sort(key=lambda x: x[0], reverse=True)
            melhor_score, melhor_est, melhor_vm = candidatos[0]

            # Ambiguidade: mais de um com score máximo
            empates = [c for c in candidatos if c[0] == melhor_score]
            if len(empates) > 1:
                nomes = ", ".join(
                    f"{c[2]['obj'].exercicio.nome}/{c[2]['obj'].nome}"
                    for c in empates[:3]
                )
                resultados.append((arquivo, None, melhor_score, "AMBÍGUO", nomes))
                continue

            variacao_obj = melhor_vm["obj"]

            # Conflito: outra variação já foi mapeada com score maior
            prev = variacoes_usadas.get(variacao_obj.id)
            if prev and prev[1] >= melhor_score:
                resultados.append((
                    arquivo, None, melhor_score, "CONFLITO",
                    f"variação já mapeada para {prev[0].name}"
                ))
                continue

            variacoes_usadas[variacao_obj.id] = (arquivo, melhor_score)
            resultados.append((arquivo, variacao_obj, melhor_score, melhor_est, ""))

        # --- Imprime relatório ---
        self._imprimir_relatorio(resultados, prefix, apply_mode)

        # --- Apply ---
        if not apply_mode:
            self.stdout.write(
                self.style.WARNING(
                    "\n  MODO PREVIEW — nenhum registro foi alterado.\n"
                    f"  Use --apply para persistir matches com score >= {SCORE_AUTO_APPLY}.\n"
                )
            )
            return

        if prefix is None:
            raise CommandError(
                "Não foi possível determinar o prefixo relativo ao MEDIA_ROOT.\n"
                "Use --prefix para especificar. Ex: --prefix exercicios/gif"
            )

        aplicados  = 0
        baixo_score = 0
        sem_match  = 0
        conflitos  = 0

        for arquivo, variacao_obj, score, estrategia, nota in resultados:
            if variacao_obj is None:
                if estrategia in ("AMBÍGUO", "CONFLITO"):
                    conflitos += 1
                else:
                    sem_match += 1
                continue

            if score < SCORE_AUTO_APPLY:
                baixo_score += 1
                continue

            caminho = f"{prefix}/{arquivo.name}"
            variacao_obj.gif = caminho
            variacao_obj.save(update_fields=["gif"])
            aplicados += 1

        self._imprimir_resumo_apply(aplicados, baixo_score, sem_match, conflitos)

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _imprimir_relatorio(self, resultados, prefix, apply_mode):
        W = 100
        modo = "APPLY" if apply_mode else "PREVIEW"

        self.stdout.write("")
        self.stdout.write("─" * W)
        self.stdout.write(
            self.style.HTTP_INFO(f"  mapear_gifs_v2 — MODO {modo}")
        )
        self.stdout.write("─" * W)
        self.stdout.write(
            f"  {'ARQUIVO':<36} {'VARIAÇÃO':<32} {'SCORE':>5}  {'ESTRATÉGIA':<22} AÇÃO"
        )
        self.stdout.write("─" * W)

        for arquivo, variacao_obj, score, estrategia, nota in resultados:
            nome_arq = arquivo.name[:35]

            if variacao_obj is None:
                var_str = (f"← {nota[:28]}" if nota else "—")[:31]
                if estrategia == "AMBÍGUO":
                    acao = self.style.WARNING("AMBÍGUO - verificar")
                elif estrategia == "CONFLITO":
                    acao = self.style.WARNING(f"CONFLITO")
                else:
                    acao = self.style.ERROR("SEM MATCH")
                score_str = f"{score:>4}%" if score else "   —"
            else:
                var_str = f"{variacao_obj.exercicio.nome} / {variacao_obj.nome}"[:31]
                score_str = f"{score:>4}%"

                if score >= SCORE_AUTO_APPLY:
                    acao = self.style.SUCCESS(
                        "→ APLICAR" if apply_mode else "→ aplicar com --apply"
                    )
                else:
                    acao = self.style.WARNING(
                        f"score baixo ({score}%) — verificar manualmente"
                    )

            self.stdout.write(
                f"  {nome_arq:<36} {var_str:<32} {score_str}  {estrategia:<22} {acao}"
            )

        self.stdout.write("─" * W)

        # Sumário de contagens
        total      = len(resultados)
        auto_ok    = sum(1 for _, v, s, _, _ in resultados if v and s >= SCORE_AUTO_APPLY)
        baixo      = sum(1 for _, v, s, _, _ in resultados if v and s < SCORE_AUTO_APPLY)
        ambiguos   = sum(1 for _, v, _, e, _ in resultados if v is None and e == "AMBÍGUO")
        conflitos  = sum(1 for _, v, _, e, _ in resultados if v is None and e == "CONFLITO")
        sem_match  = sum(1 for _, v, _, e, _ in resultados if v is None and e == "NO_MATCH")

        self.stdout.write(
            f"  Total arquivos: {total}  |  "
            f"Auto-aplicáveis (≥{SCORE_AUTO_APPLY}%): {auto_ok}  |  "
            f"Score baixo (<{SCORE_AUTO_APPLY}%): {baixo}  |  "
            f"Ambíguos: {ambiguos}  |  "
            f"Conflitos: {conflitos}  |  "
            f"Sem match: {sem_match}"
        )
        self.stdout.write("─" * W)

        if prefix:
            self.stdout.write(
                f"  Prefixo no banco: {prefix}/<arquivo>"
            )
        self.stdout.write("")

    def _imprimir_resumo_apply(self, aplicados, baixo_score, sem_match, conflitos):
        W = 100
        self.stdout.write("─" * W)
        self.stdout.write(self.style.SUCCESS(f"  ✓ APPLY CONCLUÍDO"))
        self.stdout.write("─" * W)
        self.stdout.write(f"  Registros atualizados : {aplicados}")
        self.stdout.write(
            f"  Score baixo (ignorados): {baixo_score}  "
            f"← rode --preview para ver quais e ajuste manualmente"
        )
        self.stdout.write(
            f"  Ambíguos/conflitos     : {conflitos}  "
            f"← requerem intervenção manual"
        )
        self.stdout.write(
            f"  Sem match              : {sem_match}  "
            f"← arquivos sem correspondência no banco"
        )
        self.stdout.write("─" * W)
        self.stdout.write("")
