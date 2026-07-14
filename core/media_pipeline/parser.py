"""Interpretação semântica leve de nomes de exercícios, independente do catálogo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .normalizer import display_name, normalize_name

_EXPLICIT_SEPARATOR = re.compile(r"\s+(?:-|:|–|—)\s+")


@dataclass(frozen=True, slots=True)
class ParsedExerciseName:
    original_name: str
    exercise: str
    variation: str
    normalized_exercise: str
    normalized_variation: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ParserConfig:
    default_exercise_words: int = 1


class ExerciseNameParser:
    """Extrai exercício/variação por convenção, sem dicionário de exercícios.

    Use ``Exercício - Variação`` para nomes compostos inequívocos. Na ausência
    desse separador a convenção é o primeiro termo como exercício, o restante
    como variação; o agrupador futuro poderá elevar essa inferência por corpus.
    """

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def parse(self, name: str | Path) -> ParsedExerciseName:
        original = Path(name).stem if isinstance(name, Path) else Path(name).stem
        # Detecta o separador antes de ``display_name`` converter hífens em espaço.
        explicit = _EXPLICIT_SEPARATOR.split(original, maxsplit=1)
        if len(explicit) == 2:
            exercise, variation = (display_name(part) for part in explicit)
            confidence = 1.0
        else:
            visible = display_name(original)
            words = visible.split()
            boundary = min(self.config.default_exercise_words, len(words))
            exercise = " ".join(words[:boundary])
            variation = " ".join(words[boundary:])
            confidence = 0.65 if variation else 0.8
        return ParsedExerciseName(
            original_name=original,
            exercise=exercise,
            variation=variation,
            normalized_exercise=normalize_name(exercise),
            normalized_variation=normalize_name(variation),
            confidence=confidence,
        )
