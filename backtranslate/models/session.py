from dataclasses import dataclass


@dataclass
class Session:
    id: int
    name: str
    total_sentences: int
    completed_sentences: int
    created_at: str  # ISO format datetime string

    @property
    def is_complete(self) -> bool:
        return self.completed_sentences >= self.total_sentences

    @property
    def progress_percent(self) -> float:
        if self.total_sentences == 0:
            return 0.0
        return round(self.completed_sentences / self.total_sentences * 100, 1)
