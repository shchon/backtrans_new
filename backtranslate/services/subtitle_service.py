from backtranslate.database import operations as db
from backtranslate.models import SubtitleLine


class SubtitleService:
    def get_by_session(self, session_id: int) -> list[SubtitleLine]:
        rows = db.get_subtitles_for_session(session_id)
        return [
            SubtitleLine(
                id=r["id"], idx=r["idx"], chinese=r["chinese"],
                english_official=r["english_official"],
                prev_chinese=r.get("prev_chinese", ""),
                prev_english=r.get("prev_english", ""),
                next_chinese=r.get("next_chinese", ""),
                next_english=r.get("next_english", ""),
            )
            for r in rows
        ]

    def save_batch(self, session_id: int, subtitles: list[dict]) -> None:
        db.create_subtitles_batch(session_id, subtitles)
