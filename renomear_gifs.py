import os
import unicodedata
import re

PASTA = "media/exercicios/gif"

def normalizar(nome):
    nome = unicodedata.normalize('NFKD', nome)
    nome = nome.encode('ASCII', 'ignore').decode('ASCII')
    nome = nome.lower()
    nome = nome.replace(' ', '_')
    nome = re.sub(r'[^a-z0-9_.-]', '', nome)
    return nome

for arquivo in os.listdir(PASTA):
    antigo = os.path.join(PASTA, arquivo)

    if not os.path.isfile(antigo):
        continue

    novo_nome = normalizar(arquivo)
    novo = os.path.join(PASTA, novo_nome)

    if antigo != novo:
        os.rename(antigo, novo)
        print(f'{arquivo} -> {novo_nome}')