from backtranslate.database import operations as db


class StatsService:
    def record_sentence_completed(self) -> None:
        db.record_sentence_completed()

    def get_today_count(self) -> int:
        return db.get_today_stats()

    def get_total_count(self) -> int:
        return db.get_total_sentences()

    def get_streak_days(self) -> int:
        return db.get_streak_days()

    def get_all(self) -> dict:
        return db.get_all_stats()
