import os
import django
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projeto.settings')
django.setup()

from core.models import VariacaoExercicio

sem_gif = []

for v in VariacaoExercicio.objects.all():
    valor = (
        VariacaoExercicio.objects
        .filter(id=v.id)
        .values_list("gif", flat=True)
        .first()
    )

    if not valor:
        sem_gif.append([
        v.id,
        getattr(v.exercicio, "nome", ""),
        v.nome
        ])

print(f"Total sem GIF: {len(sem_gif)}")
with open("variacoes_sem_gif.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "exercicio", "variacao"])
    writer.writerows(sem_gif)

print("Arquivo gerado: variacoes_sem_gif.csv")
      
    