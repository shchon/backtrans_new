from backtranslate.database import operations as db
from backtranslate.models import Translation


class TranslationService:
    def create(self, subtitle_id: int, user_input: str,
               version: int = 1) -> Translation:
        trans_id = db.create_translation(subtitle_id, user_input, version)
        rows = db.get_all_translations_for_subtitle(subtitle_id)
        for r in rows:
            if r["id"] == trans_id:
                return Translation(**r)
        return Translation(
            id=trans_id,
            subtitle_id=subtitle_id,
            version=version,
            user_input=user_input,
            created_at="",
        )

    def get_by_subtitle(self, subtitle_id: int) -> list[Translation]:
        rows = db.get_all_translations_for_subtitle(subtitle_id)
        return [Translation(**r) for r in rows]
