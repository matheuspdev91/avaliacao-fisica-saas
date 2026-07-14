from django.core.management.base import BaseCommand

from media_pipeline.scanner import scan_directory
from media_pipeline.inventory import salvar_inventario
from media_pipeline.utils import validar_pasta


class Command(BaseCommand):

    help = "Escaneia toda a biblioteca de mídias."

    def add_arguments(self, parser):

        parser.add_argument(
            "--path",
            required=True,
            help="Pasta raiz da biblioteca.",
        )

    def handle(self, *args, **options):

        pasta = validar_pasta(options["path"])

        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write("FITFLIX MEDIA SCANNER")
        self.stdout.write("=" * 50)

        inventario = scan_directory(pasta)

        salvar_inventario(
            inventario,
            "media_pipeline/inventario.json",
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(inventario)} arquivos encontrados."
            )
        )