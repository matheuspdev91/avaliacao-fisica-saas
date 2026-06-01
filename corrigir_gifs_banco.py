"""
corrigir_gifs_banco.py
======================
Script de reparo pontual para registros VariacaoExercicio onde gif.name
foi salvo como None ou URL incompleta pelo upload_gifs_cloudinary.py (bug corrigido).

COMO USAR:
  python manage.py shell < corrigir_gifs_banco.py

SEGURO: apenas lê e imprime por padrão.
Para aplicar: defina APLICAR = True.
"""

from core.models import VariacaoExercicio

APLICAR = False  # ← mude para True para persistir as correções

variacoes = VariacaoExercicio.objects.all()

sem_gif        = []  # gif.name vazio ou None
gif_sem_ext    = []  # tem valor mas não termina em extensão conhecida
gif_ok         = []  # URL completa e correta

EXTENSOES = ('.gif', '.mp4', '.webp', '.png', '.jpg', '.jpeg')

for v in variacoes:
    nome = (v.gif.name or '').strip()
    if not nome:
        sem_gif.append(v)
    elif nome.startswith(('http://', 'https://')):
        if any(nome.lower().endswith(ext) for ext in EXTENSOES):
            gif_ok.append(v)
        else:
            gif_sem_ext.append(v)
    else:
        # caminho relativo — pode ou não ter extensão
        if any(nome.lower().endswith(ext) for ext in EXTENSOES):
            gif_ok.append(v)
        else:
            gif_sem_ext.append(v)

print(f"\n{'='*60}")
print(f"  RELATÓRIO — gif.name no banco")
print(f"{'='*60}")
print(f"  OK (URL completa com extensão):    {len(gif_ok)}")
print(f"  SEM GIF (campo vazio):             {len(sem_gif)}")
print(f"  URL SEM EXTENSÃO (bug antigo):     {len(gif_sem_ext)}")
print(f"{'='*60}\n")

if gif_sem_ext:
    print("URLs sem extensão (seriam 404):")
    for v in gif_sem_ext:
        print(f"  ID={v.id} | {v.exercicio.nome} / {v.nome}")
        print(f"    gif.name = {repr(v.gif.name)}")
        corrigido = v.gif.name + '.gif'
        print(f"    → corrigido: {repr(corrigido)}")
        if APLICAR:
            v.gif.name = corrigido
            v.save(update_fields=['gif'])
            print(f"    ✓ Salvo.")
    print()

if not APLICAR and gif_sem_ext:
    print("Para aplicar as correções: mude APLICAR = True e rode novamente.\n")
elif APLICAR and gif_sem_ext:
    print(f"✓ {len(gif_sem_ext)} registro(s) corrigido(s).\n")
else:
    print("Nenhuma correção necessária.\n")
