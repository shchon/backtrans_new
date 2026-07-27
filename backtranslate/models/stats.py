from dataclasses import dataclass


@dataclass
class LearningStats:
    date: str
    sentence_count: int
    session_count: int


@dataclass
class StreakEntry:
    date: str
    sentences_completed: int
