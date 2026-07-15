"""Testes unitários do pipeline, sem inicializar Django ou banco de dados."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from .inventory import load_inventory, save_inventory
from .models import Inventory, MediaFile
from .normalizer import normalize_name
from .parser import ExerciseNameParser
from .scanner import MediaScanner


class NormalizerTests(unittest.TestCase):
    def test_removes_known_file_artifacts(self) -> None:
        self.assertEqual(
            normalize_name("Supino-Reto (2)_final.gif"),
            "supino reto",
        )


class ParserTests(unittest.TestCase):
    def test_splits_conventional_name(self) -> None:
        parsed = ExerciseNameParser().parse("Supino Inclinado Barra.gif")
        self.assertEqual(parsed.exercise, "Supino")
        self.assertEqual(parsed.variation, "Inclinado Barra")

    def test_honours_explicit_separator_for_compound_exercise(self) -> None:
        parsed = ExerciseNameParser().parse("Levantamento Terra - Romeno.gif")
        self.assertEqual(parsed.exercise, "Levantamento Terra")
        self.assertEqual(parsed.variation, "Romeno")


class ScannerTests(unittest.TestCase):
    def test_builds_asset_from_variable_depth_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            media_file = root / "GIFS" / "ACADEMIA" / "PEITORAL" / "Supino_Reto.gif"
            media_file.parent.mkdir(parents=True)
            media_file.write_bytes(b"GIF89a")

            media = MediaScanner().scan(root).media_files[0]

        self.assertEqual(media.category, "GIFS / ACADEMIA")
        self.assertEqual(media.muscle_group, "PEITORAL")
        self.assertEqual(media.normalized_name, "supino reto")
        self.assertEqual(len(media.sha256), 64)


class InventoryPersistenceTests(unittest.TestCase):
    def test_round_trips_media_file_with_current_and_legacy_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "inventario.json"
            media = MediaFile(
                path=Path("midias/peitoral/supino.gif"),
                category="GIFS / ACADEMIA",
                muscle_group="PEITORAL",
                filename="supino.gif",
                stem="supino",
                normalized_name="supino",
                extension=".gif",
                size=6,
                sha256="a" * 64,
            )
            save_inventory(Inventory(media_files=[media]), path)
            loaded = load_inventory(path)

        self.assertEqual(loaded.media_files, [media])


if __name__ == "__main__":
    unittest.main()
