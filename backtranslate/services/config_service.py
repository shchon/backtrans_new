from backtranslate.config import load_config, save_config
from backtranslate.models import AppSettings


class ConfigService:
    def load(self) -> AppSettings:
        raw = load_config()
        return AppSettings(
            base_url=raw.get("base_url", "https://api.deepseek.com"),
            api_key=raw.get("api_key", ""),
            model=raw.get("model", "deepseek-chat"),
            context_n=raw.get("context_n", 1),
            font_size=raw.get("font_size", 16),
            prompt_template=raw.get("prompt_template", ""),
            recent_pairs=raw.get("recent_pairs", []),
            favorite_dirs=raw.get("favorite_dirs", []),
        )

    def save(self, settings: AppSettings) -> None:
        save_config({
            "base_url": settings.base_url,
            "api_key": settings.api_key,
            "model": settings.model,
            "context_n": settings.context_n,
            "font_size": settings.font_size,
            "prompt_template": settings.prompt_template,
            "recent_pairs": settings.recent_pairs,
            "favorite_dirs": settings.favorite_dirs,
        })
