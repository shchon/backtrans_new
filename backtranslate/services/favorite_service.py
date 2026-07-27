from backtranslate.database import operations as db


class FavoriteService:
    def add(self, subtitle_id: int) -> None:
        db.add_favorite(subtitle_id)

    def remove(self, subtitle_id: int) -> None:
        db.remove_favorite(subtitle_id)

    def is_favorited(self, subtitle_id: int) -> bool:
        return db.is_favorite(subtitle_id)

    def list_all(self) -> list[dict]:
        return db.get_favorites()

    def clear_all(self) -> None:
        db.clear_favorites()
