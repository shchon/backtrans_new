from typing import Optional
from backtranslate.database import operations as db
from backtranslate.models import Session


class SessionService:
    def create(self, name: str, total: int) -> Session:
        session_id = db.create_session(name, total)
        row = db.get_session(session_id)
        return Session(**row)

    def get(self, session_id: int) -> Optional[Session]:
        row = db.get_session(session_id)
        return Session(**row) if row else None

    def update_progress(self, session_id: int, completed: int) -> None:
        db.update_session_completed(session_id, completed)

    def clear_all(self) -> None:
        db.clear_session_data()
