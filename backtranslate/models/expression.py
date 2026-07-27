from dataclasses import dataclass


@dataclass
class Expression:
    id: int
    phrase: str
    source_subtitle_id: int
    notes: str = ""
