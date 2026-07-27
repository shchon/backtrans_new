from dataclasses import dataclass, field


@dataclass
class AppSettings:
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    model: str = "deepseek-chat"
    context_n: int = 1
    font_size: int = 16
    prompt_template: str = ""
    recent_pairs: list[dict] = field(default_factory=list)
    favorite_dirs: list[str] = field(default_factory=list)
