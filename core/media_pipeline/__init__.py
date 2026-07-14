"""Pipeline independente de banco para catalogar a biblioteca de mídias.

Este pacote não importa Django nem os modelos do FitFlix.  Ele pode, portanto,
ser executado em uma estação de curadoria antes que qualquer dado seja gravado.
"""

from .inventory import MediaAsset, MediaInventory
from .parser import ExerciseNameParser, ParsedExerciseName
from .scanner import MediaScanner, ScannerConfig

__all__ = [
    "ExerciseNameParser",
    "MediaAsset",
    "MediaInventory",
    "MediaScanner",
    "ParsedExerciseName",
    "ScannerConfig",
]
