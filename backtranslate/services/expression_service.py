from backtranslate.database import operations as db
from backtranslate.models import Expression


class ExpressionService:
    def add(self, phrase: str, source_subtitle_id: int = 0,
            notes: str = "") -> Expression:
        expr_id = db.add_expression(phrase, source_subtitle_id, notes)
        return Expression(id=expr_id, phrase=phrase,
                          source_subtitle_id=source_subtitle_id, notes=notes)

    def search(self, query: str = "") -> list[Expression]:
        rows = db.get_all_expressions()
        result = [Expression(**r) for r in rows]
        if query:
            q = query.lower()
            result = [e for e in result if q in e.phrase.lower()]
        return result

    def list_all(self) -> list[Expression]:
        return self.search()

    def delete(self, expr_id: int) -> None:
        db.delete_expression(expr_id)
