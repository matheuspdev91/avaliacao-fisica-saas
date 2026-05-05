from django.core.management.base import BaseCommand
from core.models import GrupoMuscular, VariacaoExercicio, VideoExercicio

EXERCICIOS_POR_GRUPO = {
    "Peito": [
        {
            "nome": "Supino",
            "descricao": "Exercicio base para peitoral.",
            "variacoes": [
                "Reto barra",
                "Reto halter",
                "Inclinado barra",
                "Inclinado halter",
                "Máquina",
            ],
        },
        {
            "nome": "Crucifixo",
            "variacoes": ["Reto halter", "Inclinado halter", "Máquina", "Cross (cabo)"],
        },
    ],
    "Costas": [
        {
            "nome": "Remada",
            "variacoes": ["Curvada barra", "Unilateral halter", "Máquina", "Cavalinho"],
        },
        {
            "nome": "Puxada",
            "variacoes": ["Frontal aberta", "Frontal fechada", "Neutra", "Supinada"],
        },
    ],
}


class Command(BaseCommand):
    help = "Popula o banco com grupos musculares, exercícios e variações."

    def handle(self, *args, **options):
        grupos_criados = 0
        exercicios_criados = 0
        variacoes_criadas = 0

        for nome_grupo, exercicios_data in EXERCICIOS_POR_GRUPO.items():

            # ===== GRUPO =====
            grupo, criado = GrupoMuscular.objects.get_or_create(nome=nome_grupo)

            if criado:
                grupos_criados += 1
                self.stdout.write(self.style.SUCCESS(f"✔ Grupo criado: {grupo.nome}"))
            else:
                self.stdout.write(f"- Já existe grupo: {grupo.nome}")

            # ===== EXERCÍCIOS =====
            for exercicio_data in exercicios_data:

                exercicio, criado = VideoExercicio.objects.get_or_create(
                    nome=exercicio_data["nome"],
                    grupo_muscular=grupo,
                    defaults={"descricao": exercicio_data.get("descricao", "")},
                )

                if criado:
                    exercicios_criados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✔ Exercício criado: {exercicio.nome}")
                    )
                else:
                    self.stdout.write(f"- Já existe exercício: {exercicio.nome}")

                # ===== VARIAÇÕES =====
                variacoes = exercicio_data.get("variacoes", ["Padrão"])

                for nome_variacao in variacoes:
                    variacao, criada = VariacaoExercicio.objects.get_or_create(
                        exercicio=exercicio,
                        nome=nome_variacao,
                        defaults={"grupo_muscular": grupo},
                    )

                    if criada:
                        variacoes_criadas += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✔ Variação criada: {variacao.nome}")
                        )
                    else:
                        self.stdout.write(f"- Já existe variação: {variacao.nome}")

        # ===== RESUMO =====
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed concluída:\n"
                f"✔ Grupos criados: {grupos_criados}\n"
                f"✔ Exercícios criados: {exercicios_criados}\n"
                f"✔ Variações criadas: {variacoes_criadas}"
            )
        )
