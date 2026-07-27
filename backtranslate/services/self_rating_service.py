from typing import Optional
from backtranslate.database import operations as db
from backtranslate.models import SelfRating


class SelfRatingService:
    def save(self, subtitle_id: int, rating: int) -> None:
        db.upsert_self_rating(subtitle_id, rating)

    def get_by_subtitle(self, subtitle_id: int) -> Optional[SelfRating]:
        rating = db.get_self_rating(subtitle_id)
        if rating is None:
            return None
        return SelfRating(subtitle_id=subtitle_id, rating=rating)
