import json
from typing import Optional
from backtranslate.database import operations as db
from backtranslate.models import Evaluation


class EvaluationService:
    def create(self, translation_id: int,
               status: str = "pending") -> int:
        return db.create_evaluation(translation_id, status)

    def update(self, eval_id: int, status: str,
               meaning_score: Optional[float] = None,
               grammar_score: Optional[float] = None,
               naturalness_score: Optional[float] = None,
               subtitle_style_score: Optional[float] = None,
               analysis: Optional[str] = None,
               suggested: Optional[str] = None,
               error: Optional[str] = None) -> None:
        db.update_evaluation_status(
            eval_id, status, meaning_score, grammar_score,
            naturalness_score, subtitle_style_score,
            analysis, suggested, error,
        )

    def save_result(self, translation_id: int,
                    result: dict) -> int:
        """Create evaluation with AI result data in one call."""
        eval_id = db.create_evaluation(translation_id, "done")
        db.update_evaluation_status(
            eval_id, "done",
            result.get("meaning_score"),
            result.get("grammar_score"),
            result.get("naturalness_score"),
            result.get("subtitle_style_score"),
            result.get("analysis"),
            result.get("suggested_expressions"),
        )
        return eval_id

    def get_by_translation(self, translation_id: int) -> Optional[Evaluation]:
        row = db.get_evaluation_for_translation(translation_id)
        if not row:
            return None
        return self._row_to_eval(row)

    def get_all_for_session(self, session_id: int) -> list[Evaluation]:
        rows = db.get_evaluations_for_session(session_id)
        return [self._row_to_eval(r) for r in rows]

    def _row_to_eval(self, row: dict) -> Evaluation:
        suggested = row.get("suggested_expressions", "")
        if isinstance(suggested, str):
            try:
                suggested = json.loads(suggested) if suggested else []
            except (json.JSONDecodeError, TypeError):
                suggested = suggested.split("\n") if suggested else []
        return Evaluation(
            id=row["id"],
            translation_id=row["translation_id"],
            meaning_score=row.get("meaning_score") or 0,
            grammar_score=row.get("grammar_score") or 0,
            naturalness_score=row.get("naturalness_score") or 0,
            subtitle_style_score=row.get("subtitle_style_score") or 0,
            analysis_text=row.get("analysis_text") or "",
            suggested_expressions=suggested if isinstance(suggested, list) else [],
        )
