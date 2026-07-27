from backtranslate.ai.client import call_ai
from backtranslate.models import SubtitleLine


class AiService:
    @staticmethod
    def build_context(subtitles: list[SubtitleLine],
                      current_idx: int,
                      context_n: int) -> str:
        """Build surrounding context for a subtitle at current_idx."""
        if context_n == 0:
            return ""
        parts = []
        for s in subtitles:
            if s.idx < current_idx and s.idx >= current_idx - context_n:
                parts.append(f"前一句: {s.chinese}")
            elif s.idx > current_idx and s.idx <= current_idx + context_n:
                parts.append(f"后一句: {s.chinese}")
        if parts:
            return "上下文（仅供参考，不参与评分）:\n" + "\n".join(parts)
        return ""

    @staticmethod
    def evaluate(base_url: str, api_key: str, model: str,
                 prompt_template: str, context: str,
                 user_input: str, official: str) -> dict | None:
        return call_ai(base_url, api_key, model,
                       prompt_template, context,
                       user_input, official)

    @staticmethod
    def test_connection(base_url: str, api_key: str,
                        model: str) -> bool:
        result = call_ai(base_url, api_key, model,
                         "hello", "", "", "")
        return result is not None
