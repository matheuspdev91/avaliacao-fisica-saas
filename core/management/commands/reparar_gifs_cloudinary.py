from django.core.management.base import BaseCommand
from core.models import VariacaoExercicio

from cloudinary.uploader import upload

from difflib import SequenceMatcher

import os
import re
import unicodedata


class Command(BaseCommand):
    help = "Repara gifs quebradas do Cloudinary"

    PASTA_GIFS = "media/exercicios/gif"

    SCORE_MINIMO = 0.72

    PALAVRAS_OBRIGATORIAS = {
    "smith",
    "barra",
    "halter",
    "sentado",
    "unilateral",
    "cabo",
    "leg",
    "maquina",
    "corda",
    "banco",
}

    IGNORAR_PALAVRAS = {
        "gif",
        "exercicio",
        "treino",
    }

    def normalizar(self, texto):
        """
        Remove:
        - acentos
        - espaços
        - hífens
        - caracteres especiais

        Padroniza tudo.
        """

        texto = str(texto).lower()

        texto = unicodedata.normalize("NFKD", texto)
        texto = texto.encode("ascii", "ignore").decode("utf-8")

        texto = texto.replace("-", "_")
        texto = texto.replace(" ", "_")

        texto = re.sub(r"[^a-z0-9_]", "", texto)

        partes = texto.split("_")

        partes = [
            p for p in partes
            if p and p not in self.IGNORAR_PALAVRAS
        ]

        return "_".join(partes)

    def similaridade(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def buscar_melhor_arquivo(self, nome_referencia):
        """
        Procura o GIF mais parecido.
        """

        melhor_arquivo = None
        melhor_score = 0

        try:
            arquivos = os.listdir(self.PASTA_GIFS)

        except Exception as e:
            print(f"❌ Erro ao listar pasta: {e}")
            return None, 0

        for arquivo in arquivos:

            nome_arquivo = os.path.splitext(arquivo)[0]

            nome_arquivo_limpo = self.normalizar(nome_arquivo)

            # Validação de palavras obrigatórias

            falhou = False

            for palavra in self.PALAVRAS_OBRIGATORIAS:

                referencia_tem = palavra in nome_referencia.split("_")
                arquivo_tem = palavra in nome_arquivo_limpo.split("_")

                if referencia_tem != arquivo_tem:
                    falhou = True
                    break

            if falhou:
                continue

            score = self.similaridade(
                nome_referencia,
                nome_arquivo_limpo
            )

            print(
                f"🔍 {nome_referencia}  <->  "
                f"{nome_arquivo_limpo} "
                f"({score:.2f})"
            )

            # BONUS:
            # prioridade pra match exato parcial

            if nome_referencia in nome_arquivo_limpo:
                score += 0.15

            if score > melhor_score:
                melhor_score = score
                melhor_arquivo = arquivo

        return melhor_arquivo, melhor_score

    def handle(self, *args, **kwargs):

        corrigidos = 0
        ignorados = 0
        erros = 0
        nao_encontrados = 0

        variacoes = VariacaoExercicio.objects.exclude(gif="")

        print("\n🚀 INICIANDO REPARAÇÃO DE GIFS\n")

        for variacao in variacoes:

            try:

                gif_atual = str(variacao.gif)

                print("\n===================================")
                print(f"🧠 VARIAÇÃO: {variacao.id}")
                print(f"📌 Exercício: {variacao.exercicio.nome}")
                print(f"📌 Variação: {variacao.nome}")
                print(f"📌 Atual: {gif_atual}")

                # Já está ok

                if (
                    "res.cloudinary.com" in gif_atual
                    and "/upload/" in gif_atual
                ):
                    print("✅ Já está funcionando")
                    ignorados += 1
                    continue

                nome_base = (
                    f"{variacao.exercicio.nome}_"
                    f"{variacao.nome}"
                )

                nome_limpo = self.normalizar(nome_base)

                print(f"🧹 Nome limpo: {nome_limpo}")

                arquivo_encontrado, score = (
                    self.buscar_melhor_arquivo(nome_limpo)
                )

                # Score ruim

                if (
                    not arquivo_encontrado
                    or score < self.SCORE_MINIMO
                ):
                    print("❌ Nenhum match confiável encontrado")
                    nao_encontrados += 1
                    continue

                caminho_completo = os.path.join(
                    self.PASTA_GIFS,
                    arquivo_encontrado
                )

                if not os.path.exists(caminho_completo):
                    print("❌ Arquivo não existe")
                    erros += 1
                    continue

                print(f"🎯 Melhor match: {arquivo_encontrado}")
                print(f"📊 Score: {score:.2f}")

                print("📤 Enviando para Cloudinary...")

                resultado = upload(
                    caminho_completo,
                    resource_type="image",
                    folder="exercicios/gif"
                )

                variacao.gif = resultado["public_id"] + "." + resultado.get("format", "gif")
                variacao.save()

                print("✅ CORRIGIDO")

                corrigidos += 1

            except Exception as e:

                print(f"❌ ERRO: {e}")

                erros += 1

        print("\n===================================")
        print("📋 RELATÓRIO FINAL")
        print("===================================")

        print(f"✅ Corrigidos: {corrigidos}")
        print(f"⏭️ Ignorados: {ignorados}")
        print(f"❌ Não encontrados: {nao_encontrados}")
        print(f"💥 Erros: {erros}")

        print("\n🏁 FINALIZADO\n")