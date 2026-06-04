import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projeto.settings")
django.setup()

from core.models import VariacaoExercicio

url_completa = 0
public_id = 0
vazio = 0
erro = 0

ex_url = []
ex_pid = []
ex_vazio = []
ex_erro = []

for v in VariacaoExercicio.objects.all():

    try:
        valor_db = (
            VariacaoExercicio.objects
            .filter(id=v.id)
            .values_list("gif", flat=True)
            .first()
        )

        if not valor_db:
            vazio += 1

            if len(ex_vazio) < 5:
                ex_vazio.append((v.id, v.nome))

        elif str(valor_db).startswith("http"):
            url_completa += 1

            if len(ex_url) < 5:
                ex_url.append((v.id, v.nome, valor_db))

        else:
            public_id += 1

            if len(ex_pid) < 5:
                ex_pid.append((v.id, v.nome, valor_db))

    except Exception as e:
        erro += 1

        if len(ex_erro) < 5:
            ex_erro.append((v.id, str(e)))

print("\n" + "=" * 60)
print("RESUMO")
print("=" * 60)

print("URL completa :", url_completa)
print("Public ID    :", public_id)
print("Vazio        :", vazio)
print("Erro         :", erro)

print("\nEXEMPLOS URL COMPLETA")
for item in ex_url:
    print(item)

print("\nEXEMPLOS PUBLIC ID")
for item in ex_pid:
    print(item)

print("\nEXEMPLOS VAZIOS")
for item in ex_vazio:
    print(item)

print("\nEXEMPLOS ERROS")
for item in ex_erro:
    print(item)