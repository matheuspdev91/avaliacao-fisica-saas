from __future__ import annotations

from .parser import ParsedExerciseName
from .models import MatchResult

class ExerciseMatcher:
    """
    Resolve um ParsedExerciseName para um exercício conhecido.

    TODO
    ----
    - Buscar candidatos no Inventory
    - Calcular score
    - Aplicar aliases
    - Resolver ambiguidades
    """

    def __init__(self, inventory) -> None:
        self.inventory = inventory

    def match(self, parsed: ParsedExerciseName) -> MatchResult:
        """
        Executa o pipeline completo de matching.
        """

        if not parsed.exercise:
            return MatchResult(
                matched=False,
                exercise=None,
                variation=None,
                score=0.0,
                reason="empty exercise",
            )

        candidates = self._find_candidates(parsed)

        if not candidates:
            return MatchResult(
                matched=False,
                exercise=None,
                variation=None,
                score=0.0,
                reason="no candidates",
            )

        return self._best_candidate(parsed, candidates)

    def _find_candidates(self, parsed: ParsedExerciseName):
        """
        Retorna possíveis candidatos do Inventory.

        Implementação temporária.
        """
        return []

    def _best_candidate(
        self,
        parsed: ParsedExerciseName,
        candidates,
    ) -> MatchResult:
        """
        Escolhe o candidato com maior score.

        Implementação temporária.
        """

        candidate = candidates[0]

        return MatchResult(
            matched=True,
            exercise=candidate.exercise,
            variation=candidate.variation,
            score=self._score_candidate(parsed, candidate),
            reason="best candidate",
        )

    def _score_candidate(
        self,
        parsed: ParsedExerciseName,
        candidate,
    ) -> float:
        """
        Calcula o score de similaridade entre parser e candidato.

        Implementação temporária.
        """
        return 1.0