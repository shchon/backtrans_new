from dataclasses import dataclass, field


@dataclass
class Translation:
    id: int
    subtitle_id: int
    version: int
    user_input: str
    created_at: str  # ISO format


@dataclass
class Evaluation:
    id: int
    translation_id: int
    meaning_score: int
    grammar_score: int
    naturalness_score: int
    subtitle_style_score: int
    analysis_text: str
    suggested_expressions: list[str] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        return round(
            (self.meaning_score + self.grammar_score
             + self.naturalness_score + self.subtitle_style_score) / 4, 1
        )


@dataclass
class SelfRating:
    subtitle_id: int
    rating: int  # 1-5
