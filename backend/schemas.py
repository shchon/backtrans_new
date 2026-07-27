from pydantic import BaseModel
from typing import Optional


class SessionResponse(BaseModel):
    id: int
    name: str
    total_sentences: int
    completed_sentences: int
    created_at: str


class SubtitleItem(BaseModel):
    id: int
    idx: int
    chinese: str
    english_official: str
    prev_chinese: str = ""
    prev_english: str = ""
    next_chinese: str = ""
    next_english: str = ""


class StatsResponse(BaseModel):
    today: int
    total: int
    streak: int


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class SubtitleListResponse(BaseModel):
    subtitles: list[SubtitleItem]
    session: Optional[SessionResponse] = None


# ===== Step 3: AI + Config =====

class TranslateRequest(BaseModel):
    subtitle_id: int
    user_input: str

class TranslateResponse(BaseModel):
    translation_id: int
    eval_id: int
    status: str

class EvaluationStatus(BaseModel):
    id: int
    status: str  # pending | done | failed
    meaning_score: Optional[int] = None
    grammar_score: Optional[int] = None
    naturalness_score: Optional[int] = None
    subtitle_style_score: Optional[int] = None
    analysis_text: Optional[str] = None
    suggested_expressions: list[str] = []
    error_message: Optional[str] = None

class EvaluationListResponse(BaseModel):
    evaluations: list[EvaluationStatus]

class ConfigResponse(BaseModel):
    base_url: str
    api_key: str
    model: str
    context_n: int
    font_size: int
    prompt_template: str

class ConfigUpdateRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    context_n: Optional[int] = None
    font_size: Optional[int] = None
    prompt_template: Optional[str] = None


# ===== Step 3: Import + Expressions + Favorites =====

class SrtImportRequest(BaseModel):
    chinese_srt: str
    english_srt: str
    use_timecode: bool = False
    name: str = ""

class SrtImportResponse(BaseModel):
    session: SessionResponse
    subtitles: list[SubtitleItem]

class ExpressionCreateRequest(BaseModel):
    phrase: str
    subtitle_id: int = 0

class ExpressionItem(BaseModel):
    id: int
    phrase: str
    notes: str = ""
    source_subtitle_id: Optional[int] = None

class ExpressionListResponse(BaseModel):
    expressions: list[ExpressionItem]
