from core.models import VariacaoExercicio
from difflib import SequenceMatcher
import os

PASTA = "COSTAS"

arquivos = [
    os.path.splitext(f)[0].lower()
    for f in os.listdir(PASTA)
    if f.lower().endswith(".gif")
]

print("\n==VARIAÇÕES SEM GIF===\n")

for v in VariacaoExercicio.objects.filter(
    exercicio__nome__icontains="remada"
):
    if v.gif:
        continue

    melhor = None
    score = 0

    nome  = v.nome.lower()

    for arquivo in arquivos:
        s = SequenceMatcher(None, nome, arquivo).ratio()

        if s > score:

            score = s
            melhor = arquivo

    print(
        f"{v.id} - {v.nome}\n"
        f" melhor match: {melhor}\n"
        f" score: {score:.2f}\n"
    )
    

        