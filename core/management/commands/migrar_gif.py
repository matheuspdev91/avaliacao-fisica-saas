from django.core.management.base import BaseCommand
from core.models import VideoExercicio, VariacaoExercicio
from core.models import GrupoMuscular
from core.util.texto import nome_bonito

import os
import re
import unicodedata

BASE_PATH = "/home/matheus/Área de trabalho/django_pratica/media/exercicios/gif"

# =========================
# NORMALIZAÇÃO
# =========================


def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# =========================
# EXERCÍCIOS BASE
# =========================

BASE_MAP = {
    # Bíceps
    "rosca martelo": "Rosca Martelo",
    "rosca scott": "Rosca Scott",
    "rosca alternada": "Rosca Alternada",
    "rosca": "Rosca",

    # Tríceps
    "triceps testa": "Tríceps Testa",
    "triceps frances": "Tríceps Francês",
    "triceps": "Tríceps",

    # Peitoral
    "supino": "Supino",
    "crucifixo": "Crucifixo",
    "cross": "Cross Over",
    "anilha press": "Anilha Press",

    # Costas
    "remada": "Remada",
    "puxada": "Puxada",
    "maquina de remo": "Remada",
    "pullover": "Pullover",
    "serrote": "Serrote",
    "barra fixa": "Barra Fixa",
    "pull up": "Pull Up",
    "pulldown": "Pulldown",

    # Ombros
    "desenvolvimento": "Desenvolvimento",
    "elevacao lateral": "Elevação Lateral",
    "voador para deltoides": "Crucifixo Inverso",
    "voador invertido": "Crucifixo Inverso",
    "crucifixo inverso": "Crucifixo Inverso",
    "deltoide posterior": "Crucifixo Inverso",
    "levantamento frontal": "Elevação Frontal",
    "elevacao frontal": "Elevação Frontal",

    # Pernas
    "agachamento": "Agachamento",
    "leg press": "Leg Press",
    "flexora": "Mesa Flexora",
    "extensora": "Cadeira Extensora",
    "levantamento terra": "Levantamento Terra",
    "terra romeno": "Levantamento Terra",
    "stiff": "Stiff",
    "afundo": "Afundo",
    "leg press": "Leg Press",
    "mesa flexora": "Mesa Flexora",
    "cadeira flexora": "Cadeira Flexora",
    "cadeira extensora": "Cadeira Extensora",
    "flexao nordica": "Flexão Nórdica",
    "bom dia": "Bom Dia",
    "avanco": "Afundo",

    # Glúteos
    "gluteo": "Glúteo",
    "maquina de abducao": "Abdução",
    "abducao de quadril": "Abdução",
    "aducao de quadril": "Adução",
    "elevacao pelvica": "Elevação Pélvica",
    "ponte": "Elevação Pélvica",

    # Panturrilhas
    "panturrilha": "Panturrilha",
    
    # Abdômen
    "abdominal": "Abdominal",
    "prancha": "Prancha",
    "abdominais": "Abdominal",
    "abdominais obliquos": "Abdominal Oblíquo",
    "abducao": "Abdução",
    "aducao": "Adução",
    "alpinista": "Mountain Climber",
    "superman": "Superman",
    "inseto morto": "Dead Bug",
    "besouro morto": "Dead Bug",
    "posicao do barco": "Barco",
    "canoinha": "Barco",
    "toque de calcanhar": "Toque de Calcanhar",
    "elevacao de pernas": "Elevação de Pernas",
    "step": "Step Up",
    "subida no step": "Step Up",
    "pes a barra": "Pés à Barra",

    # Cardio
    "airbike": "Airbike",
    "eliptica": "Elíptica",
    "eliptico": "Elíptica",
    "escada": "Escada",
    "polichinelo": "Polichinelo",
    "bicicleta": "Bike",
    "bicicleta ergometrica": "Bike",
    "esteira": "Esteira",
    "corrida": "Corrida",
    "corda de batalha": "Corda de Batalha",

    # Funcional
    "burpee": "Burpee",

    # CALISTENIA
    "paralela": "Paralela",
    "paralelas": "Paralela",
    "muscle up": "Muscle Up",
    "planche": "Planche",
    "back lever": "Back Lever",
    "bandeira humana": "Bandeira Humana",
    "suspensao passiva": "Suspensão Passiva",
    "mergulho coreano": "Mergulho Coreano",
    "back lever": "Back Lever",
    "bandeira humana": "Bandeira Humana",
    "back lever": "Back Lever",
    "bandeira humana": "Bandeira Humana",

    # ABDÔMEN
    "sit up": "Sit Up",
    "v up": "V Up",
    "dragon flag": "Dragon Flag",
    "wall sit": "Wall Sit",
    "wallsit": "Wall Sit",
    "l sit": "L Sit",
    "superman": "Superman",
    "inseto morto": "Dead Bug",
    "besouro morto": "Dead Bug",
    "posicao do barco": "Barco",
    "canoinha": "Barco",
    "toque de calcanhar": "Toque de Calcanhar",
    "elevacao de pernas": "Elevação de Pernas",
    "pes a barra": "Pés à Barra",
    "torcao": "Torção",
    "giro": "Torção",

    # Mobilidade
    "alongamento": "Alongamento",
    "rolamento": "Alongamento",
    "rolo de espuma": "Alongamento",
    "rotacao externa": "Rotação Externa",
    "rotacao interna": "Rotação Interna",
    "pendulo de ombro": "Pêndulo de Ombro",
    "rolagem de espuma": "Liberação Miofascial",
}

def detectar_base(nome):
    nome = normalizar(nome)

    for chave in sorted(BASE_MAP.keys(), key=len, reverse=True):
        if chave in nome:
            return BASE_MAP[chave]
    return "Outro"

# ===============
# LIMPAR NOME
# ===============

def limpar_nome(nome):
    nome = os.path.splitext(nome)[0]
    nome = nome.replace("_", " ").replace("-", " ")
    return nome.strip()

# DETECTAR GRUPO

def detectar_grupo(caminho):
    pasta = os.path.basename(os.path.dirname(caminho))
    pasta = normalizar(pasta)

    for chave, grupo in GRUPO_MAP.items():
        if chave in pasta:
            return grupo
    return "Outros"

# =======================
# DETECTAR CATEGORIA
# =======================

def detectar_categoria(nome):
    nome = normalizar(nome)

    for chave, categoria in CATEGORIA_MAP.items():
        if chave in nome:
            return categoria
    return "Outros"

# ========================
# MAPA DOS GRUPOS
# ========================
GRUPO_MAP = {
    # Musculação
    "biceps": "Bíceps",
    "bíceps": "Bíceps",
    "triceps": "Tríceps",
    "tríceps": "Tríceps",
    "peitoral": "Peitoral",
    "costas": "Costas",
    "ombros": "Ombros",
    "pernas": "Pernas",
    "gluteos": "Glúteos",
    "glúteos": "Glúteos",
    "panturrilha": "Panturrilhas",
    "panturrilhas": "Panturrilhas",
   
    # Novas categorias
    "gifs abdominais": "Abdômen",
    "gifs calistenia": "Calistenia",
    "gifs treinamento funcional": "Funcional",
    "gifs mobilidade alongamento liberacao": "Mobilidade",

    # Fallbacks
    "abdominal": "Abdômen",
    "abdominais": "Abdômen",
    "calistenia": "Calistenia",
    "funcional": "Funcional",
    "mobilidade": "Mobilidade",
    "alongamento": "Mobilidade",
    "liberacao": "Mobilidade",
    "liberação": "Mobilidade",
}

# ===================
# CATEGORIA MAP
# ===================

CATEGORIA_MAP = {
    # Musculação
    "supino": "Força",
    "crucifixo": "Força",
    "cross": "Força",
    "remada": "Força",
    "puxada": "Força",
    "agachamento": "Força",
    "leg press": "Força",
    "afundo": "Força",
    "stiff": "Força",
    "mesa flexora": "Força",
    "cadeira extensora": "Força",
    "cadeira flexora": "Força",
    "rosca": "Força",
    "triceps": "Força",
    "desenvolvimento": "Força",
    # Cardio
    "corrida": "Cardio",
    "bike": "Cardio",
    "esteira": "Cardio",
    "airbike": "Cardio",
    # Calistenia
    "barra fixa": "Calistenia",
    "pull up": "Calistenia",
    "muscle up": "Calistenia",
    "paralela": "Calistenia",
    "flexao": "Calistenia",
    # Funcional
    "burpee": "Funcional",
    "kettlebell": "Funcional",
    # Mobilidade
    "mobilidade": "Mobilidade",
    "alongamento": "Mobilidade",
    "liberacao": "Mobilidade",
    # Abdômen
    "abdominal": "Abdômen",
    "prancha": "Abdômen",
}

# =========================
# COMMAND
# =========================
class Command(BaseCommand):
    help = "Criar exercícios e variações automaticamente a partir dos GIFs"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        arquivos = []
        for root, dirs, files in os.walk(BASE_PATH):
            for f in files:
                if f.lower().endswith(".gif"):
                    arquivos.append(os.path.join(root, f))

        self.stdout.write(f"📦 TOTAL DE GIFs: {len(arquivos)}\n")

        criados = 0
        outros = []

        for caminho in arquivos:
            nome_arquivo = os.path.basename(caminho)
            nome_limpo = limpar_nome(nome_arquivo)
            variacao_nome = nome_bonito(nome_limpo)

            if not variacao_nome.strip():
                variacao_nome = "Exercicio"

            grupo_nome_raw = detectar_grupo(caminho)
            grupo, _ = GrupoMuscular.objects.get_or_create(nome=grupo_nome_raw)

            base = detectar_base(nome_limpo)
            if base == "Outro":
                outros.append(nome_limpo)
            categoria = detectar_categoria(nome_limpo)

            if base == "Outro":
                exercicio_nome = "Outros"

            else:
                exercicio_nome = base

            exercicio, _ = VideoExercicio.objects.get_or_create(
                nome=exercicio_nome,
                defaults={"grupo_muscular": grupo, "categoria": categoria},
            )

            # Caso exista sem grupo

            alterou = False

            if not exercicio.grupo_muscular:
                exercicio.grupo_muscular = grupo
                alterou = True

            if not exercicio.categoria:
                exercicio.categoria = categoria
                alterou = True

            if alterou:
                exercicio.save()

            variacao_nome = nome_bonito(nome_limpo)

            variacao, created = VariacaoExercicio.objects.get_or_create(
                exercicio=exercicio, nome=variacao_nome
            )

            if created:
                criados += 1

            if not dry_run:
                variacao.gif = caminho
                variacao.save()

            self.stdout.write(
                f"✅ {nome_arquivo} -> {exercicio.nome} / {variacao.nome}"
            )

        self.stdout.write(f"⚠️ NÃO MAPEADOS: {len(outros)}")

        if outros:
            self.stdout.write("\nEXERCICIOS NÃO MAPEADOS:\n")

            for nome in sorted(set(outros)):
                self.stdout.write(f" - {nome}")

        self.stdout.write("\n=========================")
        self.stdout.write(f"🔥 VARIAÇÕES CRIADAS: {criados}")
        self.stdout.write("=========================")
