from dataclasses import dataclass, field


@dataclass
class SubtitlePair:
    """SRT 解析配对后的原始字幕对"""
    index: int
    chinese_text: str
    english_text: str
    start_ms: int = 0
    end_ms: int = 0


@dataclass
class SubtitleLine:
    """应用层字幕行（含上下文信息）"""
    idx: int
    chinese: str
    english_official: str
    prev_chinese: str = ""
    prev_english: str = ""
    next_chinese: str = ""
    next_english: str = ""
    id: int = 0  # database id
