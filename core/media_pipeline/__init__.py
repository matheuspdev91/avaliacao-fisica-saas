"""Pipeline independente de banco para catalogar a biblioteca de mídias.

Este pacote não importa Django nem os modelos do FitFlix.  Ele pode, portanto,
ser executado em uma estação de curadoria antes que qualquer dado seja gravado.
"""

from .inventory import load_inventory, save_inventory
from .models import Exercise, Inventory, MatchResult, MediaFile, Variation
from .parser import ExerciseNameParser, ParsedExerciseName
from .scanner import MediaScanner, ScannerConfig

__all__ = [
    "ExerciseNameParser",
    "Exercise",
    "Inventory",
    "load_inventory",
    "MatchResult",
    "MediaFile",
    "MediaScanner",
    "ParsedExerciseName",
    "ScannerConfig",
    "save_inventory",
    "Variation",
]
