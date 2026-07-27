import json
import re
import requests


def build_prompt(template: str, context: str, user_input: str, official: str) -> str:
    return template.format(context=context, user_input=user_input, official=official)


def parse_ai_response(raw_content: str) -> dict | None:
    content = raw_content.strip()
    # Try to extract JSON from markdown code fence
    m = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", content)
    if m:
        content = m.group(1).strip()
    try:
        data = json.loads(content)
        return {
            "meaning_score": int(data.get("meaning_score", 0)),
            "grammar_score": int(data.get("grammar_score", 0)),
            "naturalness_score": int(data.get("naturalness_score", 0)),
            "subtitle_style_score": int(data.get("subtitle_style_score", 0)),
            "analysis": data.get("analysis", ""),
            "suggested_expressions": data.get("suggested_expressions", []),
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def call_ai(
    base_url: str,
    api_key: str,
    model: str,
    prompt_template: str,
    context: str,
    user_input: str,
    official: str,
) -> dict | None:
    prompt = build_prompt(prompt_template, context, user_input, official)
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError):
        return None

    return parse_ai_response(content)
