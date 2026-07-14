"""Testes unitários do pipeline, sem inicializar Django ou banco de dados."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

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

            asset = MediaScanner().scan(root).assets[0]

        self.assertEqual(asset.category, "GIFS / ACADEMIA")
        self.assertEqual(asset.muscle_group, "PEITORAL")
        self.assertEqual(asset.normalized_name, "supino reto")
        self.assertEqual(len(asset.sha256), 64)


if __name__ == "__main__":
    unittest.main()
