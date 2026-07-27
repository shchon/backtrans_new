# BackTranslate MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PySide6 desktop app for subtitle back-translation training with async AI evaluation.

**Architecture:** 4-page single-window app (Learn, Review, Expressions, Settings). SRT parsing + pairing feeds into a Sprint translation loop. Each translation triggers a background QThread worker that calls OpenAI-compatible API for evaluation. Results stored in SQLite, reviewed post-session.

**Tech Stack:** Python 3.11+, PySide6, SQLite, `requests` for HTTP, `pytest` for tests

**Project root:** `i:\python\英语回译`

---

## File Structure

```
backtranslate/
├── __init__.py
├── main.py                         # Entry point, QApplication setup
├── config.py                       # JSON settings file read/write
├── defaults.py                     # Default config values + default Prompt text
├── database/
│   ├── __init__.py
│   ├── connection.py               # SQLite connection, schema creation
│   └── operations.py               # All CRUD functions
├── srt/
│   ├── __init__.py
│   ├── parser.py                   # Parse .srt files into list of dicts
│   └── pairing.py                  # Timecode-based and line-number-based pairing
├── ai/
│   ├── __init__.py
│   ├── client.py                   # Synchronous OpenAI-compatible API call
│   └── worker.py                   # QThread worker: queue → API → store results
└── ui/
    ├── __init__.py
    ├── main_window.py              # QMainWindow + sidebar nav + stacked widget
    ├── learn_page.py               # Import SRT + Sprint translation loop
    ├── review_page.py              # Review list + detail panel
    ├── expressions_page.py         # Expression library browser
    └── settings_page.py            # Settings form
```

---

### Task 1: Project Scaffold & Config

**Files:**
- Create: `backtranslate/__init__.py`
- Create: `backtranslate/defaults.py`
- Create: `backtranslate/config.py`

- [ ] **Step 1: Create `backtranslate/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backtranslate/defaults.py`**

```python
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_CONTEXT_N = 1
DEFAULT_PROMPT_TEMPLATE = """You are a professional subtitle translator and language coach. Analyze the user's English translation of the given Chinese subtitle.

{context}

User's translation: "{user_input}"

Official English subtitle: "{official}"

Evaluate the translation on these four dimensions (each 0-100), then provide a brief analysis and highlight useful expressions worth remembering.

Return ONLY valid JSON with this exact structure (no markdown, no extra text):
{{
  "meaning_score": 0-100,
  "grammar_score": 0-100,
  "naturalness_score": 0-100,
  "subtitle_style_score": 0-100,
  "analysis": "Concise analysis in the user's language (Chinese). Compare the user's translation with the official one. Explain WHY the official translation works better or why both are valid. Focus on naturalness and subtitle conventions, not just correctness. Be encouraging.",
  "suggested_expressions": ["expression1", "expression2"]
}}"""
```

- [ ] **Step 3: Create `backtranslate/config.py`**

```python
import json
import os
from .defaults import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_CONTEXT_N,
    DEFAULT_PROMPT_TEMPLATE,
)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _default_config():
    return {
        "base_url": DEFAULT_BASE_URL,
        "api_key": "",
        "model": DEFAULT_MODEL,
        "context_n": DEFAULT_CONTEXT_N,
        "prompt_template": DEFAULT_PROMPT_TEMPLATE,
    }


def load_config():
    _ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        cfg = _default_config()
        cfg.update(saved)
        return cfg
    return _default_config()


def save_config(cfg):
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run pytest to verify import**

Run: `python -c "from backtranslate.config import load_config; print(load_config()['model'])"`
Expected: `deepseek-chat`

- [ ] **Step 5: Commit**

```bash
git add backtranslate/__init__.py backtranslate/defaults.py backtranslate/config.py
git commit -m "feat: add project scaffold with config system"
```

---

### Task 2: SRT Parser

**Files:**
- Create: `backtranslate/srt/__init__.py`
- Create: `backtranslate/srt/parser.py`
- Create: `tests/__init__.py`
- Create: `tests/test_srt_parser.py`

- [ ] **Step 1: Create `tests/test_srt_parser.py` (failing test)**

```python
from backtranslate.srt.parser import parse_srt


def test_parse_simple_srt():
    content = """1
00:00:01,000 --> 00:00:03,000
你好

2
00:00:05,000 --> 00:00:08,000
再见
"""
    result = parse_srt(content)
    assert len(result) == 2
    assert result[0]["index"] == 1
    assert result[0]["start"] == 1000
    assert result[0]["end"] == 3000
    assert result[0]["text"] == "你好"
    assert result[1]["index"] == 2
    assert result[1]["text"] == "再见"


def test_parse_srt_with_milliseconds():
    content = """1
00:01:30,500 --> 00:01:35,200
测试字幕
"""
    result = parse_srt(content)
    assert result[0]["start"] == 90500
    assert result[0]["end"] == 95200


def test_parse_empty_srt():
    result = parse_srt("")
    assert result == []


def test_parse_srt_strips_html_tags_in_text():
    content = """1
00:00:01,000 --> 00:00:03,000
<i>斜体文字</i>
"""
    result = parse_srt(content)
    assert "<i>" not in result[0]["text"]
```

- [ ] **Step 2: Run tests to see them fail**

Run: `pytest tests/test_srt_parser.py -v`
Expected: ModuleNotFoundError (no parse_srt function)

- [ ] **Step 3: Create `backtranslate/srt/__init__.py`**

Empty file.

- [ ] **Step 4: Create `backtranslate/srt/parser.py`**

```python
import re


def _timestamp_to_ms(ts):
    h, m, s_ms = ts.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)


def _strip_tags(text):
    return re.sub(r"<[^>]+>", "", text)


def parse_srt(content):
    """Parse SRT content into list of dicts with keys: index, start, end, text."""
    if not content.strip():
        return []

    blocks = [b.strip() for b in content.strip().split("\n\n") if b.strip()]
    result = []

    pattern = re.compile(
        r"^(\d+)\s*\n"
        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n"
        r"([\s\S]+)$",
        re.MULTILINE,
    )

    for block in blocks:
        m = pattern.match(block)
        if not m:
            continue
        idx_str, start_ts, end_ts, text = m.groups()
        result.append({
            "index": int(idx_str),
            "start": _timestamp_to_ms(start_ts),
            "end": _timestamp_to_ms(end_ts),
            "text": _strip_tags(text.strip()),
        })

    return result
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_srt_parser.py -v`
Expected: all 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backtranslate/srt/ tests/
git commit -m "feat: add SRT parser"
```

---

### Task 3: SRT Pairing

**Files:**
- Create: `backtranslate/srt/pairing.py`
- Create: `tests/test_srt_pairing.py`

- [ ] **Step 1: Create `tests/test_srt_pairing.py`**

```python
from backtranslate.srt.pairing import pair_by_index, pair_by_timecode


def _ch(text):
    return {"index": 0, "start": 0, "end": 0, "text": text}


def make_entry(index, start, end, text):
    return {"index": index, "start": start, "end": end, "text": text}


def test_pair_by_index_equal_lengths():
    ch_list = [_ch("你好"), _ch("再见")]
    en_list = [_ch("Hello"), _ch("Goodbye")]
    result = pair_by_index(ch_list, en_list)
    assert len(result) == 2
    assert result[0] == (ch_list[0], en_list[0])
    assert result[1] == (ch_list[1], en_list[1])


def test_pair_by_index_mismatched_lengths():
    ch_list = [_ch("你好"), _ch("再见"), _ch("谢谢")]
    en_list = [_ch("Hello"), _ch("Goodbye")]
    result = pair_by_index(ch_list, en_list)
    assert len(result) == 2


def test_pair_by_timecode_overlap():
    ch_list = [
        make_entry(1, 1000, 3000, "你好"),
        make_entry(2, 4000, 6000, "再见"),
    ]
    en_list = [
        make_entry(1, 1200, 2800, "Hello"),
        make_entry(2, 4100, 5900, "Goodbye"),
    ]
    result = pair_by_timecode(ch_list, en_list)
    assert len(result) == 2
    assert result[0][0]["text"] == "你好"
    assert result[0][1]["text"] == "Hello"


def test_pair_by_timecode_no_overlap():
    ch_list = [make_entry(1, 1000, 2000, "你好")]
    en_list = [make_entry(1, 3000, 4000, "Hello")]
    result = pair_by_timecode(ch_list, en_list)
    assert len(result) == 0
```

- [ ] **Step 2: Run tests to see them fail**

Run: `pytest tests/test_srt_pairing.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Create `backtranslate/srt/pairing.py`**

```python
def pair_by_index(chinese_list, english_list):
    """Pair by sequential index. Stops at the shorter list length."""
    pairs = []
    for i in range(min(len(chinese_list), len(english_list))):
        pairs.append((chinese_list[i], english_list[i]))
    return pairs


def pair_by_timecode(chinese_list, english_list):
    """Pair subtitles with overlapping time ranges."""
    pairs = []

    ci = 0
    ei = 0
    while ci < len(chinese_list) and ei < len(english_list):
        ch = chinese_list[ci]
        en = english_list[ei]

        overlap_start = max(ch["start"], en["start"])
        overlap_end = min(ch["end"], en["end"])

        if overlap_start < overlap_end:
            pairs.append((ch, en))
            ci += 1
            ei += 1
        elif ch["start"] < en["start"]:
            ci += 1
        else:
            ei += 1

    return pairs
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_srt_pairing.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backtranslate/srt/pairing.py tests/test_srt_pairing.py
git commit -m "feat: add SRT pairing (index and timecode)"
```

---

### Task 4: Database Schema & Connection

**Files:**
- Create: `backtranslate/database/__init__.py`
- Create: `backtranslate/database/connection.py`

- [ ] **Step 1: Create `backtranslate/database/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backtranslate/database/connection.py`**

```python
import sqlite3
import os

DB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"
)
DB_PATH = os.path.join(DB_DIR, "backtranslate.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_sentences INTEGER DEFAULT 0,
    completed_sentences INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subtitles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    idx INTEGER,
    chinese TEXT,
    english_official TEXT,
    prev_chinese TEXT,
    prev_english TEXT,
    next_chinese TEXT,
    next_english TEXT
);

CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtitle_id INTEGER REFERENCES subtitles(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,
    user_input TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id INTEGER REFERENCES translations(id) ON DELETE CASCADE,
    meaning_score INTEGER,
    grammar_score INTEGER,
    naturalness_score INTEGER,
    subtitle_style_score INTEGER,
    analysis_text TEXT,
    suggested_expressions TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase TEXT,
    source_subtitle_id INTEGER,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS self_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtitle_id INTEGER UNIQUE REFERENCES subtitles(id) ON DELETE CASCADE,
    rating INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
```

- [ ] **Step 3: Verify DB init works**

Run: `python -c "from backtranslate.database.connection import init_db; init_db(); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backtranslate/database/__init__.py backtranslate/database/connection.py
git commit -m "feat: add database schema and connection"
```

---

### Task 5: Database CRUD Operations

**Files:**
- Create: `backtranslate/database/operations.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Create `tests/test_database.py`**

```python
import pytest
from backtranslate.database.connection import init_db, get_connection
from backtranslate.database.operations import (
    create_session,
    create_subtitles_batch,
    get_session,
    get_subtitles_for_session,
    create_translation,
    get_latest_translation,
    get_all_translations_for_subtitle,
    create_evaluation,
    update_evaluation_status,
    get_evaluation_for_translation,
    add_expression,
    get_all_expressions,
    delete_expression,
    upsert_self_rating,
    get_self_rating,
    clear_session_data,
)


@pytest.fixture
def db():
    init_db()
    conn = get_connection()
    yield conn
    conn.close()


def test_create_and_get_session(db):
    sid = create_session("Test Movie", 50)
    assert sid > 0
    session = get_session(sid)
    assert session["name"] == "Test Movie"
    assert session["total_sentences"] == 50


def test_create_subtitles_batch(db):
    sid = create_session("Test", 2)
    subs = [
        {"idx": 1, "chinese": "你好", "english_official": "Hello"},
        {"idx": 2, "chinese": "再见", "english_official": "Goodbye"},
    ]
    create_subtitles_batch(sid, subs)
    result = get_subtitles_for_session(sid)
    assert len(result) == 2
    assert result[0]["chinese"] == "你好"


def test_create_and_get_translations(db):
    sid = create_session("Test", 1)
    sub = {"idx": 1, "chinese": "你好", "english_official": "Hello"}
    create_subtitles_batch(sid, [sub])
    subs = get_subtitles_for_session(sid)
    sub_id = subs[0]["id"]

    t1 = create_translation(sub_id, "Hi", 1)
    t2 = create_translation(sub_id, "Hey there", 2)

    assert get_latest_translation(sub_id) == "Hey there"
    all_trans = get_all_translations_for_subtitle(sub_id)
    assert len(all_trans) == 2
    assert all_trans[0]["user_input"] == "Hi"


def test_create_and_get_evaluation(db):
    sid = create_session("Test", 1)
    create_subtitles_batch(sid, [{"idx": 1, "chinese": "你好", "english_official": "Hello"}])
    subs = get_subtitles_for_session(sid)
    tid = create_translation(subs[0]["id"], "Hi", 1)

    eid = create_evaluation(tid)
    assert eid > 0

    ev = get_evaluation_for_translation(tid)
    assert ev["status"] == "pending"

    update_evaluation_status(eid, "done", 95, 100, 82, 75, "Great job", '["well done"]')
    ev = get_evaluation_for_translation(tid)
    assert ev["status"] == "done"
    assert ev["meaning_score"] == 95


def test_expressions_persistence(db):
    eid = add_expression("figure out", None, "useful phrasal verb")
    assert eid > 0
    expressions = get_all_expressions()
    assert len(expressions) == 1
    assert expressions[0]["phrase"] == "figure out"

    delete_expression(eid)
    assert len(get_all_expressions()) == 0


def test_self_rating(db):
    sid = create_session("Test", 1)
    create_subtitles_batch(sid, [{"idx": 1, "chinese": "你好", "english_official": "Hello"}])
    subs = get_subtitles_for_session(sid)
    sub_id = subs[0]["id"]

    assert get_self_rating(sub_id) is None
    upsert_self_rating(sub_id, 3)
    assert get_self_rating(sub_id) == 3
    upsert_self_rating(sub_id, 1)
    assert get_self_rating(sub_id) == 1


def test_clear_session_data(db):
    sid = create_session("Test", 1)
    create_subtitles_batch(sid, [{"idx": 1, "chinese": "你好", "english_official": "Hello"}])
    subs = get_subtitles_for_session(sid)
    add_expression("test phrase", subs[0]["id"])

    clear_session_data()

    assert get_session(sid) is None
    assert len(get_subtitles_for_session(sid)) == 0
    assert len(get_all_expressions()) == 1  # expressions survive
```

- [ ] **Step 2: Run tests to see failures**

Run: `pytest tests/test_database.py -v`
Expected: all FAIL (ImportError)

- [ ] **Step 3: Create `backtranslate/database/operations.py`**

```python
from .connection import get_connection


def create_session(name, total_sentences):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO sessions (name, total_sentences) VALUES (?, ?)",
        (name, total_sentences),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_session(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def create_subtitles_batch(session_id, subtitle_list):
    conn = get_connection()
    for sub in subtitle_list:
        conn.execute(
            """INSERT INTO subtitles
            (session_id, idx, chinese, english_official,
             prev_chinese, prev_english, next_chinese, next_english)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                sub["idx"],
                sub["chinese"],
                sub["english_official"],
                sub.get("prev_chinese", ""),
                sub.get("prev_english", ""),
                sub.get("next_chinese", ""),
                sub.get("next_english", ""),
            ),
        )
    conn.commit()
    conn.close()


def get_subtitles_for_session(session_id):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        "SELECT * FROM subtitles WHERE session_id = ? ORDER BY idx",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_translation(subtitle_id, user_input, version=1):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO translations (subtitle_id, user_input, version) VALUES (?, ?, ?)",
        (subtitle_id, user_input, version),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_latest_translation(subtitle_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT user_input FROM translations WHERE subtitle_id = ? ORDER BY version DESC LIMIT 1",
        (subtitle_id,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def get_all_translations_for_subtitle(subtitle_id):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        "SELECT * FROM translations WHERE subtitle_id = ? ORDER BY version",
        (subtitle_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_evaluation(translation_id, status="pending"):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO evaluations (translation_id, status) VALUES (?, ?)",
        (translation_id, status),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def update_evaluation_status(
    eval_id, status, meaning=None, grammar=None, naturalness=None,
    subtitle_style=None, analysis=None, suggested=None, error=None
):
    conn = get_connection()
    conn.execute(
        """UPDATE evaluations SET
            status=?, meaning_score=?, grammar_score=?,
            naturalness_score=?, subtitle_style_score=?,
            analysis_text=?, suggested_expressions=?, error_message=?
        WHERE id=?""",
        (status, meaning, grammar, naturalness, subtitle_style, analysis, suggested, error, eval_id),
    )
    conn.commit()
    conn.close()


def get_evaluation_for_translation(translation_id):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    row = conn.execute(
        "SELECT * FROM evaluations WHERE translation_id = ?",
        (translation_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_expression(phrase, source_subtitle_id=None, notes=""):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expressions (phrase, source_subtitle_id, notes) VALUES (?, ?, ?)",
        (phrase, source_subtitle_id, notes),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def get_all_expressions():
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute("SELECT * FROM expressions ORDER BY collected_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_expression(expression_id):
    conn = get_connection()
    conn.execute("DELETE FROM expressions WHERE id = ?", (expression_id,))
    conn.commit()
    conn.close()


def upsert_self_rating(subtitle_id, rating):
    conn = get_connection()
    conn.execute(
        """INSERT INTO self_ratings (subtitle_id, rating)
        VALUES (?, ?) ON CONFLICT(subtitle_id) DO UPDATE SET rating=?""",
        (subtitle_id, rating, rating),
    )
    conn.commit()
    conn.close()


def get_self_rating(subtitle_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT rating FROM self_ratings WHERE subtitle_id = ?", (subtitle_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def clear_session_data():
    conn = get_connection()
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()


def update_session_completed(session_id, count):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET completed_sentences = ? WHERE id = ?",
        (count, session_id),
    )
    conn.commit()
    conn.close()


def get_evaluations_for_session(session_id):
    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        """SELECT e.*, t.subtitle_id
        FROM evaluations e
        JOIN translations t ON e.translation_id = t.id
        JOIN subtitles s ON t.subtitle_id = s.id
        WHERE s.session_id = ?
        ORDER BY s.idx""",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_database.py -v`
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backtranslate/database/operations.py tests/test_database.py
git commit -m "feat: add database CRUD operations"
```

---

### Task 6: AI Client

**Files:**
- Create: `backtranslate/ai/__init__.py`
- Create: `backtranslate/ai/client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Create `tests/test_ai_client.py`**

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from backtranslate.ai.client import build_prompt, call_ai, parse_ai_response


def test_build_prompt():
    context = "Previous: 你好 -> Hello\nNext: 再见 -> Goodbye"
    user_input = "Hi"
    official = "Hello"
    template = "Context: {context}\nUser: {user_input}\nOfficial: {official}"
    result = build_prompt(template, context, user_input, official)
    assert "Previous:" in result
    assert "Hi" in result
    assert "Hello" in result


def test_parse_ai_response_valid_json():
    response = json.dumps({
        "meaning_score": 95,
        "grammar_score": 100,
        "naturalness_score": 82,
        "subtitle_style_score": 75,
        "analysis": "Good translation.",
        "suggested_expressions": ["well done"],
    })
    result = parse_ai_response(response)
    assert result["meaning_score"] == 95
    assert result["suggested_expressions"] == ["well done"]


def test_parse_ai_response_with_markdown_wrapper():
    response = '```json\n' + json.dumps({"meaning_score": 90, "grammar_score": 85, "naturalness_score": 80, "subtitle_style_score": 70, "analysis": "ok", "suggested_expressions": []}) + '\n```'
    result = parse_ai_response(response)
    assert result["meaning_score"] == 90


def test_parse_ai_response_invalid_json():
    result = parse_ai_response("not json at all")
    assert result is None


@patch("backtranslate.ai.client.requests.post")
def test_call_ai_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"meaning_score": 100, "grammar_score": 100, "naturalness_score": 100, "subtitle_style_score": 100, "analysis": "perfect", "suggested_expressions": []}'}}]
    }
    mock_post.return_value = mock_response

    result = call_ai(
        "http://example.com/v1",
        "sk-test",
        "test-model",
        "You are a coach.",
        "Context text",
        "user input",
        "official text",
    )
    assert result is not None
    assert result["meaning_score"] == 100


@patch("backtranslate.ai.client.requests.post")
def test_call_ai_http_error(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    result = call_ai(
        "http://example.com/v1",
        "sk-test",
        "test-model",
        "prompt template",
        "context",
        "user input",
        "official",
    )
    assert result is None
```

- [ ] **Step 2: Run tests to see failures**

Run: `pytest tests/test_ai_client.py -v`
Expected: all FAIL (ImportError)

- [ ] **Step 3: Create `backtranslate/ai/__init__.py`**

Empty file.

- [ ] **Step 4: Create `backtranslate/ai/client.py`**

```python
import json
import re
import requests


def build_prompt(template, context, user_input, official):
    return template.format(context=context, user_input=user_input, official=official)


def parse_ai_response(raw_content):
    content = raw_content.strip()
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


def call_ai(base_url, api_key, model, prompt_template, context, user_input, official):
    prompt = build_prompt(prompt_template, context, user_input, official)
    url = base_url.rstrip("/") + "/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
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
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_ai_client.py -v`
Expected: all 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backtranslate/ai/__init__.py backtranslate/ai/client.py tests/test_ai_client.py
git commit -m "feat: add AI client (OpenAI-compatible)"
```

---

### Task 7: AI Background Worker

**Files:**
- Create: `backtranslate/ai/worker.py`
- Create: `tests/test_ai_worker.py`

- [ ] **Step 1: Create `tests/test_ai_worker.py`**

```python
from unittest.mock import patch, MagicMock
from backtranslate.ai.worker import EvaluationWorker


def test_worker_process_queue_success(qtbot):
    worker = EvaluationWorker(
        base_url="http://test/v1",
        api_key="sk-test",
        model="test-model",
        prompt_template="Rate: {user_input}",
    )

    fake_result = {
        "meaning_score": 90,
        "grammar_score": 85,
        "naturalness_score": 80,
        "subtitle_style_score": 75,
        "analysis": "ok",
        "suggested_expressions": ["test"],
    }

    with patch("backtranslate.ai.worker.call_ai", return_value=fake_result):
        worker.add_task(1, 10, "hello", "hi", "context text")
        assert worker.queue.qsize() == 1

        eval_received = {}

        def on_done(eval_id, result):
            eval_received["id"] = eval_id
            eval_received["result"] = result

        worker.evaluation_done.connect(on_done)
        worker.process_next()

        assert eval_received["id"] == 1
        assert eval_received["result"]["meaning_score"] == 90


def test_worker_retry_on_failure(qtbot):
    worker = EvaluationWorker(
        base_url="http://test/v1",
        api_key="sk-test",
        model="test-model",
        prompt_template="Rate: {user_input}",
    )

    with patch("backtranslate.ai.worker.call_ai", return_value=None):
        worker.add_task(1, 20, "hello", "hi", "")
        worker.process_next()

        fail_received = {}

        def on_fail(eval_id):
            fail_received["id"] = eval_id

        worker.evaluation_failed.connect(on_fail)

        worker.process_next()
        worker.process_next()
        worker.process_next()
        worker.process_next()

    assert fail_received.get("id") == 1
```

- [ ] **Step 2: Run tests to see failures**

Run: `pytest tests/test_ai_worker.py -v`
Expected: all FAIL (ImportError)

- [ ] **Step 3: Create `backtranslate/ai/worker.py`**

```python
import json
from queue import Queue
from PySide6.QtCore import QThread, Signal, QObject

from .client import call_ai

MAX_RETRIES = 3


class EvaluationWorker(QObject):
    evaluation_done = Signal(int, object)   # eval_id, result_dict
    evaluation_failed = Signal(int)         # eval_id

    def __init__(self, base_url, api_key, model, prompt_template):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.prompt_template = prompt_template
        self.queue = Queue()
        self._retries = {}
        self._thread = None

    def add_task(self, eval_id, translation_id, user_input, official, context):
        task = {
            "eval_id": eval_id,
            "translation_id": translation_id,
            "user_input": user_input,
            "official": official,
            "context": context,
        }
        self.queue.put(task)

    def process_next(self):
        if self.queue.empty():
            return
        task = self.queue.get()

        result = call_ai(
            self.base_url,
            self.api_key,
            self.model,
            self.prompt_template,
            task["context"],
            task["user_input"],
            task["official"],
        )

        if result is not None:
            self.evaluation_done.emit(task["eval_id"], result)
            self._retries.pop(task["eval_id"], None)
        else:
            retries = self._retries.get(task["eval_id"], 0) + 1
            if retries <= MAX_RETRIES:
                self._retries[task["eval_id"]] = retries
                self.queue.put(task)
            else:
                self._retries.pop(task["eval_id"], None)
                self.evaluation_failed.emit(task["eval_id"])


class EvaluationThread(QThread):
    task_ready = Signal()

    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            self.msleep(100)
            if not self.worker.queue.empty():
                self.task_ready.emit()

    def stop(self):
        self._running = False
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_ai_worker.py -v`
Expected: all 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backtranslate/ai/worker.py tests/test_ai_worker.py
git commit -m "feat: add AI background evaluation worker"
```

---

### Task 8: Main Window Skeleton & Navigation

**Files:**
- Create: `backtranslate/ui/__init__.py`
- Create: `backtranslate/ui/main_window.py`
- Create: `backtranslate/main.py`

- [ ] **Step 1: Create `backtranslate/ui/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backtranslate/ui/main_window.py`**

```python
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QFrame,
)
from PySide6.QtCore import Qt


NAV_STYLE = """
QPushButton {
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    color: #333;
}
QPushButton:hover {
    background: #e8e8e8;
}
QPushButton[active="true"] {
    background: #d0e0ff;
    font-weight: bold;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BackTranslate - 回译训练")
        self.resize(1100, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background: #f5f5f5;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        self.nav_buttons = []
        nav_items = ["学习", "复盘", "表达库", "设置"]

        for name in nav_items:
            btn = QPushButton(name)
            btn.setStyleSheet(NAV_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self._on_nav(n))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((name, btn))

        sidebar_layout.addStretch()
        layout.addWidget(sidebar)

        # Content area
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.learn_page = None
        self.review_page = None
        self.expressions_page = None
        self.settings_page = None

        self._update_nav("学习")

    def _on_nav(self, name):
        self._update_nav(name)
        if name == "学习" and self.learn_page:
            self.stack.setCurrentWidget(self.learn_page)
        elif name == "复盘" and self.review_page:
            self.stack.setCurrentWidget(self.review_page)
        elif name == "表达库" and self.expressions_page:
            self.stack.setCurrentWidget(self.expressions_page)
        elif name == "设置" and self.settings_page:
            self.stack.setCurrentWidget(self.settings_page)

    def _update_nav(self, active_name):
        for name, btn in self.nav_buttons:
            btn.setProperty("active", name == active_name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_learn_page(self, widget):
        self.learn_page = widget
        self.stack.addWidget(widget)

    def set_review_page(self, widget):
        self.review_page = widget
        self.stack.addWidget(widget)

    def set_expressions_page(self, widget):
        self.expressions_page = widget
        self.stack.addWidget(widget)

    def set_settings_page(self, widget):
        self.settings_page = widget
        self.stack.addWidget(widget)

    def navigate_to_review(self):
        self._on_nav("复盘")
```

- [ ] **Step 3: Create `backtranslate/main.py`**

```python
import sys
from PySide6.QtWidgets import QApplication
from backtranslate.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify import works**

Run: `python -c "from backtranslate.ui.main_window import MainWindow; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backtranslate/ui/__init__.py backtranslate/ui/main_window.py backtranslate/main.py
git commit -m "feat: add main window skeleton with sidebar navigation"
```

---

### Task 9: Settings Page

**Files:**
- Create: `backtranslate/ui/settings_page.py`

- [ ] **Step 1: Create `backtranslate/ui/settings_page.py`**

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPlainTextEdit, QPushButton,
    QLabel, QGroupBox, QMessageBox,
)
from backtranslate.config import load_config, save_config
from backtranslate.defaults import (
    DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_PROMPT_TEMPLATE,
)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # AI Config group
        ai_group = QGroupBox("AI 配置")
        ai_form = QFormLayout(ai_group)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText(DEFAULT_BASE_URL)
        ai_form.addRow("Base URL:", self.base_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入 API Key")
        ai_form.addRow("API Key:", self.api_key_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(DEFAULT_MODEL)
        ai_form.addRow("Model:", self.model_input)

        self.context_n_input = QSpinBox()
        self.context_n_input.setRange(0, 5)
        self.context_n_input.setValue(1)
        ai_form.addRow("上下文字数:", self.context_n_input)

        layout.addWidget(ai_group)

        # Prompt group
        prompt_group = QGroupBox("Prompt 模板")
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_help = QLabel(
            "可用变量: {context}（上下文字幕）、{user_input}（你的翻译）、{official}（官方字幕）"
        )
        prompt_help.setStyleSheet("color: #666; font-size: 12px;")
        prompt_layout.addWidget(prompt_help)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMinimumHeight(250)
        prompt_layout.addWidget(self.prompt_edit)

        layout.addWidget(prompt_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton("恢复默认 Prompt")
        reset_btn.clicked.connect(self._reset_prompt)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 24px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #357abd; }"
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _load_config(self):
        cfg = load_config()
        self.base_url_input.setText(cfg.get("base_url", ""))
        self.api_key_input.setText(cfg.get("api_key", ""))
        self.model_input.setText(cfg.get("model", ""))
        self.context_n_input.setValue(cfg.get("context_n", 1))
        self.prompt_edit.setPlainText(cfg.get("prompt_template", ""))

    def _reset_prompt(self):
        self.prompt_edit.setPlainText(DEFAULT_PROMPT_TEMPLATE)

    def _save(self):
        cfg = {
            "base_url": self.base_url_input.text().strip() or DEFAULT_BASE_URL,
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_input.text().strip() or DEFAULT_MODEL,
            "context_n": self.context_n_input.value(),
            "prompt_template": self.prompt_edit.toPlainText() or DEFAULT_PROMPT_TEMPLATE,
        }
        save_config(cfg)
        QMessageBox.information(self, "保存成功", "设置已保存。")
```

- [ ] **Step 2: Verify import**

Run: `python -c "from backtranslate.ui.settings_page import SettingsPage; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backtranslate/ui/settings_page.py
git commit -m "feat: add settings page (AI config + prompt editor)"
```

---

### Task 10: Learn Page (Sprint Translation)

**Files:**
- Create: `backtranslate/ui/learn_page.py`

- [ ] **Step 1: Create `backtranslate/ui/learn_page.py`**

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QFileDialog, QMessageBox,
    QDialog, QVBoxLayout as QVBoxLayout2, QRadioButton, QGroupBox,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from backtranslate.srt.parser import parse_srt
from backtranslate.srt.pairing import pair_by_index, pair_by_timecode
from backtranslate.database.connection import init_db, get_connection
from backtranslate.database.operations import (
    create_session, create_subtitles_batch, create_translation,
    create_evaluation, update_session_completed,
)


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入字幕")
        self.resize(500, 250)
        self.chinese_path = ""
        self.english_path = ""

        layout = QVBoxLayout2(self)

        # Chinese SRT
        layout.addWidget(QLabel("中文 SRT 文件:"))
        ch_layout = QHBoxLayout()
        self.ch_path_label = QLabel("未选择")
        self.ch_path_label.setStyleSheet("color: #999;")
        ch_layout.addWidget(self.ch_path_label)
        ch_btn = QPushButton("选择...")
        ch_btn.clicked.connect(self._select_chinese)
        ch_layout.addWidget(ch_btn)
        layout.addLayout(ch_layout)

        # English SRT
        layout.addWidget(QLabel("英文 SRT 文件:"))
        en_layout = QHBoxLayout()
        self.en_path_label = QLabel("未选择")
        self.en_path_label.setStyleSheet("color: #999;")
        en_layout.addWidget(self.en_path_label)
        en_btn = QPushButton("选择...")
        en_btn.clicked.connect(self._select_english)
        en_layout.addWidget(en_btn)
        layout.addLayout(en_layout)

        # Pairing strategy
        pair_group = QGroupBox("配对策略")
        pair_layout = QVBoxLayout2(pair_group)
        self.by_timecode_rb = QRadioButton("按时间轴匹配")
        self.by_index_rb = QRadioButton("按序号匹配")
        self.by_timecode_rb.setChecked(True)
        pair_layout.addWidget(self.by_timecode_rb)
        pair_layout.addWidget(self.by_index_rb)
        layout.addWidget(pair_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        self.ok_btn = QPushButton("开始学习")
        self.ok_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 20px; "
            "border-radius: 4px; }"
        )
        self.ok_btn.clicked.connect(self._validate)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _select_chinese(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择中文 SRT", "", "SRT Files (*.srt)")
        if path:
            self.chinese_path = path
            self.ch_path_label.setText(path)
            self.ch_path_label.setStyleSheet("color: #333;")

    def _select_english(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择英文 SRT", "", "SRT Files (*.srt)")
        if path:
            self.english_path = path
            self.en_path_label.setText(path)
            self.en_path_label.setStyleSheet("color: #333;")

    def _validate(self):
        if not self.chinese_path or not self.english_path:
            QMessageBox.warning(self, "提示", "请选择中文和英文 SRT 文件。")
            return
        self.accept()


class LearnPage(QWidget):
    session_created = Signal(int, int)   # session_id, total count
    translation_submitted = Signal(int, int, str, str)  # eval_id, subtitle_id, user_input, official

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.subtitles = []
        self.current_idx = 0
        self.total_count = 0
        self.completed_count = 0
        self.translation_count = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Top bar
        top = QHBoxLayout()
        self.title_label = QLabel("回译训练")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        top.addWidget(self.title_label)
        top.addStretch()

        self.import_btn = QPushButton("导入字幕")
        self.import_btn.setStyleSheet(
            "QPushButton { background: #4a90d9; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #357abd; }"
        )
        self.import_btn.clicked.connect(self._show_import_dialog)
        top.addWidget(self.import_btn)

        self.end_btn = QPushButton("结束学习")
        self.end_btn.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #c0392b; }"
        )
        self.end_btn.clicked.connect(self._end_session)
        self.end_btn.setVisible(False)
        top.addWidget(self.end_btn)

        layout.addLayout(top)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #666;")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Translation area
        self.translation_area = QWidget()
        self.translation_area.setVisible(False)
        ta_layout = QVBoxLayout(self.translation_area)
        ta_layout.setContentsMargins(0, 12, 0, 0)

        self.chinese_label = QLabel("")
        font = QFont()
        font.setPointSize(18)
        self.chinese_label.setFont(font)
        self.chinese_label.setAlignment(Qt.AlignCenter)
        self.chinese_label.setMinimumHeight(80)
        self.chinese_label.setWordWrap(True)
        ta_layout.addWidget(self.chinese_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入英文翻译，按 Enter 提交...")
        self.input_field.setMinimumHeight(44)
        input_font = QFont()
        input_font.setPointSize(14)
        self.input_field.setFont(input_font)
        self.input_field.returnPressed.connect(self._submit_translation)
        ta_layout.addWidget(self.input_field)

        layout.addWidget(self.translation_area)

        # Empty state
        self.empty_label = QLabel("点击\"导入字幕\"开始学习")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-size: 16px;")
        layout.addWidget(self.empty_label)

        layout.addStretch()

    def _show_import_dialog(self):
        dlg = ImportDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._import_srt(
                dlg.chinese_path, dlg.english_path,
                dlg.by_timecode_rb.isChecked(),
            )

    def _import_srt(self, ch_path, en_path, use_timecode):
        with open(ch_path, "r", encoding="utf-8") as f:
            ch_subs = parse_srt(f.read())
        with open(en_path, "r", encoding="utf-8") as f:
            en_subs = parse_srt(f.read())

        if use_timecode:
            pairs = pair_by_timecode(ch_subs, en_subs)
        else:
            pairs = pair_by_index(ch_subs, en_subs)

        if not pairs:
            QMessageBox.warning(self, "配对失败", "没有找到可配对的中英字幕。")
            return

        init_db()
        import os
        name = os.path.splitext(os.path.basename(ch_path))[0]

        from backtranslate.database.operations import clear_session_data
        clear_session_data()

        self.session_id = create_session(name, len(pairs))
        self.total_count = len(pairs)
        self.completed_count = 0
        self.current_idx = 0

        self.subtitles = []
        for i, (ch, en) in enumerate(pairs):
            prev_ch = pairs[i - 1][0]["text"] if i > 0 else ""
            prev_en = pairs[i - 1][1]["text"] if i > 0 else ""
            next_ch = pairs[i + 1][0]["text"] if i < len(pairs) - 1 else ""
            next_en = pairs[i + 1][1]["text"] if i < len(pairs) - 1 else ""

            self.subtitles.append({
                "idx": i + 1,
                "chinese": ch["text"],
                "english_official": en["text"],
                "prev_chinese": prev_ch,
                "prev_english": prev_en,
                "next_chinese": next_ch,
                "next_english": next_en,
            })

        create_subtitles_batch(self.session_id, self.subtitles)
        self.session_created.emit(self.session_id, self.total_count)

        self._start_translation_ui()

    def _start_translation_ui(self):
        self.import_btn.setVisible(False)
        self.empty_label.setVisible(False)
        self.translation_area.setVisible(True)
        self.end_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(self.total_count)
        self.progress_label.setVisible(True)
        self._show_current_sentence()

    def _show_current_sentence(self):
        if self.current_idx >= self.total_count:
            self._end_session()
            return
        sub = self.subtitles[self.current_idx]
        self.chinese_label.setText(sub["chinese"])
        self.progress_bar.setValue(self.completed_count)
        self.progress_label.setText(
            f"第 {self.current_idx + 1}/{self.total_count} 句"
        )
        self.input_field.clear()
        self.input_field.setFocus()

    def _submit_translation(self):
        text = self.input_field.text().strip()
        if not text:
            return

        sub = self.subtitles[self.current_idx]

        subs_row = self._get_subtitle_row(self.current_idx + 1)
        if subs_row is None:
            return

        translate_id = create_translation(subs_row["id"], text, 1)
        eval_id = create_evaluation(translate_id)

        self.translation_count += 1
        self.completed_count += 1
        self.current_idx += 1

        if self.session_id:
            update_session_completed(self.session_id, self.completed_count)

        self.translation_submitted.emit(
            eval_id, subs_row["id"], text, sub["english_official"]
        )

        self._show_current_sentence()

    def _get_subtitle_row(self, idx):
        from backtranslate.database.operations import get_subtitles_for_session
        subs = get_subtitles_for_session(self.session_id)
        for s in subs:
            if s["idx"] == idx:
                return s
        return None

    def _end_session(self):
        self.input_field.setEnabled(False)
        self.translation_submitted.emit(-1, -1, "", "")  # sentinel for "session ended"

    def reset_to_start(self):
        self.session_id = None
        self.subtitles = []
        self.current_idx = 0
        self.total_count = 0
        self.completed_count = 0
        self.import_btn.setVisible(True)
        self.empty_label.setVisible(True)
        self.translation_area.setVisible(False)
        self.end_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.input_field.setEnabled(True)
        self.input_field.clear()
```

- [ ] **Step 2: Verify import**

Run: `python -c "from backtranslate.ui.learn_page import LearnPage; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backtranslate/ui/learn_page.py
git commit -m "feat: add learn page with SRT import and sprint translation"
```

---

### Task 11: Review Page

**Files:**
- Create: `backtranslate/ui/review_page.py`

- [ ] **Step 1: Create `backtranslate/ui/review_page.py`**

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QLineEdit, QMessageBox,
)
from PySide6.QtCore import Signal, Qt

from backtranslate.database.operations import (
    get_subtitles_for_session, get_latest_translation,
    get_evaluation_for_translation, create_translation,
    create_evaluation, upsert_self_rating, get_self_rating,
    get_all_translations_for_subtitle, add_expression,
)


class ReviewPage(QWidget):
    redo_submitted = Signal(int, int, str, str)  # eval_id, subtitle_id, input, official
    retry_requested = Signal(int, int, str, str)  # eval_id, subtitle_id, user_input, official

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.subtitle_rows = []
        self.detail_widgets = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("复盘")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(self.count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

    def load_session(self, session_id):
        self.session_id = session_id
        self.subtitle_rows = get_subtitles_for_session(session_id)
        self._refresh_list()

    def update_evaluation(self, subtitle_id):
        """Called when a new evaluation result arrives for a specific subtitle."""
        if str(subtitle_id) in self.detail_widgets:
            widget = self.detail_widgets[str(subtitle_id)]
            self._update_row_display(widget, self._subtitle_by_id(subtitle_id))
        else:
            self._refresh_list()

    def _refresh_list(self):
        """Rebuild the full list."""
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.detail_widgets.clear()

        completed = 0
        for sub in self.subtitle_rows:
            eval_data = self._get_latest_eval(sub["id"])
            if eval_data and eval_data["status"] == "done":
                completed += 1
            row_widget = self._build_row_widget(sub)
            self.list_layout.addWidget(row_widget)
            self.detail_widgets[str(sub["id"])] = row_widget

        self.count_label.setText(
            f"共 {len(self.subtitle_rows)} 句，已批改 {completed} 句"
        )

    def _get_latest_eval(self, subtitle_id):
        tid = self._get_latest_translation_id(subtitle_id)
        if tid is None:
            return None
        return get_evaluation_for_translation(tid)

    def _get_latest_translation_id(self, subtitle_id):
        from backtranslate.database.connection import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT id FROM translations WHERE subtitle_id = ? ORDER BY version DESC LIMIT 1",
            (subtitle_id,),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _subtitle_by_id(self, sub_id):
        for s in self.subtitle_rows:
            if s["id"] == sub_id:
                return s
        return None

    def _build_row_widget(self, sub):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { border: 1px solid #ddd; border-radius: 6px; margin: 4px 0; }"
        )
        main_layout = QVBoxLayout(frame)

        # Summary row
        summary = QHBoxLayout()
        summary.addWidget(QLabel(f"#{sub['idx']}"))
        ch_label = QLabel(sub["chinese"])
        ch_label.setStyleSheet("font-size: 14px;")
        summary.addWidget(ch_label, 1)

        eval_data = self._get_latest_eval(sub["id"])
        self._add_score_summary(summary, eval_data)
        main_layout.addLayout(summary)

        # Detail area (shown/hidden)
        detail = QWidget()
        detail.setObjectName(f"detail_{sub['id']}")
        self._build_detail_content(detail, sub, eval_data)
        main_layout.addWidget(detail)

        return frame

    def _add_score_summary(self, layout, eval_data):
        if eval_data is None or eval_data["status"] == "pending":
            lbl = QLabel("⏳ 等待批改")
            lbl.setStyleSheet("color: #888;")
            layout.addWidget(lbl)
        elif eval_data["status"] == "processing":
            lbl = QLabel("🔄 批改中")
            lbl.setStyleSheet("color: #f39c12;")
            layout.addWidget(lbl)
        elif eval_data["status"] == "failed":
            lbl = QLabel("❌ 批改失败")
            lbl.setStyleSheet("color: #e74c3c;")
            layout.addWidget(lbl)
            retry_btn = QPushButton("重试")
            retry_btn.setStyleSheet("color: #e74c3c; border: 1px solid #e74c3c; border-radius: 3px; padding: 2px 8px;")
            retry_btn.clicked.connect(lambda checked, s=sub: self._retry_eval(s, eval_data))
            layout.addWidget(retry_btn)
        elif eval_data["status"] == "done":
            avg = (eval_data["meaning_score"] + eval_data["grammar_score"]
                   + eval_data["naturalness_score"] + eval_data["subtitle_style_score"]) / 4
            color = "#27ae60" if avg >= 80 else "#f39c12" if avg >= 60 else "#e74c3c"
            lbl = QLabel(f"综合 {avg:.0f}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            layout.addWidget(lbl)

    def _build_detail_content(self, parent, sub, eval_data):
        parent_layout = QVBoxLayout(parent)

        if eval_data and eval_data["status"] == "done":
            scores_text = (
                f"意思: {eval_data['meaning_score']} | "
                f"语法: {eval_data['grammar_score']} | "
                f"自然度: {eval_data['naturalness_score']} | "
                f"字幕风格: {eval_data['subtitle_style_score']}"
            )
            scores_label = QLabel(scores_text)
            scores_label.setStyleSheet("font-size: 13px; margin-bottom: 8px;")
            parent_layout.addWidget(scores_label)

            analysis_label = QLabel(eval_data["analysis_text"] or "")
            analysis_label.setWordWrap(True)
            analysis_label.setStyleSheet("color: #333; margin-bottom: 8px;")
            parent_layout.addWidget(analysis_label)

        # Official subtitle (hidden by default)
        official_btn = QPushButton("查看官方字幕")
        official_btn.setStyleSheet("color: #4a90d9; border: none;")
        official_label = QLabel(sub["english_official"])
        official_label.setWordWrap(True)
        official_label.setVisible(False)
        parent_layout.addWidget(official_btn)
        parent_layout.addWidget(official_label)
        official_btn.clicked.connect(lambda: official_label.setVisible(not official_label.isVisible()))

        # Self rating
        rating_label = QLabel("自我评分:")
        rating_layout = QHBoxLayout()
        for emoji, val in [("😊", 3), ("😐", 2), ("😓", 1)]:
            btn = QPushButton(emoji)
            btn.setFixedSize(36, 36)
            btn.clicked.connect(lambda checked, s=sub["id"], v=val: self._set_self_rating(s, v, btn))
            rating_layout.addWidget(btn)

        current_rating = get_self_rating(sub["id"])
        parent_layout.addWidget(rating_label)
        parent_layout.addLayout(rating_layout)

        # Redo
        redo_layout = QHBoxLayout()
        redo_input = QLineEdit()
        redo_input.setPlaceholderText("重新翻译...")
        redo_btn = QPushButton("提交")
        redo_btn.clicked.connect(lambda: self._submit_redo(sub, redo_input))
        redo_layout.addWidget(redo_input, 1)
        redo_layout.addWidget(redo_btn)
        parent_layout.addLayout(redo_layout)

        # Version history
        versions = get_all_translations_for_subtitle(sub["id"])
        if len(versions) > 1:
            ver_label = QLabel(f"共 {len(versions)} 个版本:")
            ver_label.setStyleSheet("color: #666; font-size: 12px;")
            parent_layout.addWidget(ver_label)
            for v in versions:
                parent_layout.addWidget(QLabel(f"  v{v['version']}: {v['user_input']}"))

        # Collect expression
        if eval_data and eval_data["suggested_expressions"]:
            import json
            try:
                suggested = json.loads(eval_data["suggested_expressions"])
            except (json.JSONDecodeError, TypeError):
                suggested = []
            for expr in suggested:
                collect_btn = QPushButton(f"收藏: {expr}")
                collect_btn.clicked.connect(lambda checked, e=expr, s=sub["id"]: self._collect(e, s))
                parent_layout.addWidget(collect_btn)

        # Manual collect
        manual_layout = QHBoxLayout()
        manual_input = QLineEdit()
        manual_input.setPlaceholderText("手动添加表达...")
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(lambda: self._collect(manual_input.text(), sub["id"]))
        manual_layout.addWidget(manual_input, 1)
        manual_layout.addWidget(add_btn)
        parent_layout.addLayout(manual_layout)

    def _set_self_rating(self, subtitle_id, rating, btn):
        upsert_self_rating(subtitle_id, rating)

    def _retry_eval(self, sub, eval_data):
        """Re-queue a failed evaluation for retry."""
        translation = get_latest_translation(sub["id"])
        if translation:
            from backtranslate.database.operations import update_evaluation_status as ues
            ues(eval_data["id"], "pending")
            self.retry_requested.emit(
                eval_data["id"], sub["id"], translation, sub["english_official"]
            )

    def _submit_redo(self, sub, input_widget):
        text = input_widget.text().strip()
        if not text:
            return
        tid = self._get_latest_translation_id(sub["id"])
        version = 1
        if tid:
            ev = get_evaluation_for_translation(tid)
            if ev:
                from backtranslate.database.connection import get_connection
                conn = get_connection()
                row = conn.execute(
                    "SELECT MAX(version) FROM translations WHERE subtitle_id = ?",
                    (sub["id"],),
                ).fetchone()
                conn.close()
                version = (row[0] or 0) + 1

        translate_id = create_translation(sub["id"], text, version)
        eval_id = create_evaluation(translate_id)
        self.redo_submitted.emit(eval_id, sub["id"], text, sub["english_official"])
        input_widget.clear()
        QMessageBox.information(self, "已提交", "重新翻译已提交 AI 批改。")

    def _collect(self, phrase, subtitle_id):
        if phrase.strip():
            add_expression(phrase.strip(), subtitle_id)
            QMessageBox.information(self, "已收藏", f"已收藏: {phrase}")

    def _update_row_display(self, widget, sub):
        """Refresh a single row widget when new evaluation arrives."""
        idx = self.list_layout.indexOf(widget)
        if idx >= 0:
            self.list_layout.takeAt(idx)
            widget.deleteLater()
        new_widget = self._build_row_widget(sub)
        self.list_layout.insertWidget(idx if idx >= 0 else self.list_layout.count(), new_widget)
        self.detail_widgets[str(sub["id"])] = new_widget
```

- [ ] **Step 2: Verify import**

Run: `python -c "from backtranslate.ui.review_page import ReviewPage; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backtranslate/ui/review_page.py
git commit -m "feat: add review page with evaluation list and detail panel"
```

---

### Task 12: Expressions Page

**Files:**
- Create: `backtranslate/ui/expressions_page.py`

- [ ] **Step 1: Create `backtranslate/ui/expressions_page.py`**

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QLineEdit, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt

from backtranslate.database.operations import get_all_expressions, delete_expression


class ExpressionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("表达库")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索表达...")
        self.search_input.textChanged.connect(self._filter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        self._refresh()

    def _refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        expressions = get_all_expressions()
        query = self.search_input.text().strip().lower()

        for expr in expressions:
            if query and query not in expr["phrase"].lower():
                continue

            frame = QFrame()
            frame.setStyleSheet(
                "QFrame { border: 1px solid #ddd; border-radius: 6px; margin: 4px 0; padding: 8px; }"
            )
            row = QHBoxLayout(frame)

            phrase_label = QLabel(expr["phrase"])
            phrase_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            row.addWidget(phrase_label)

            if expr["notes"]:
                notes_label = QLabel(expr["notes"])
                notes_label.setStyleSheet("color: #666;")
                row.addWidget(notes_label)

            row.addStretch()

            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("color: #e74c3c; border: none;")
            delete_btn.clicked.connect(
                lambda checked, eid=expr["id"]: self._delete_expression(eid)
            )
            row.addWidget(delete_btn)

            self.list_layout.addWidget(frame)

        if self.list_layout.count() == 0:
            empty = QLabel("还没有收藏的表达")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #999; font-size: 16px; margin-top: 60px;")
            self.list_layout.addWidget(empty)

    def _filter(self):
        self._refresh()

    def _delete_expression(self, expression_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个表达吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            delete_expression(expression_id)
            self._refresh()
```

- [ ] **Step 2: Verify import**

Run: `python -c "from backtranslate.ui.expressions_page import ExpressionsPage; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backtranslate/ui/expressions_page.py
git commit -m "feat: add expressions library page"
```

---

### Task 13: Integration — Wiring Everything in main.py

**Files:**
- Modify: `backtranslate/main.py`

- [ ] **Step 1: Rewrite `backtranslate/main.py` with full integration**

```python
import sys
import json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from backtranslate.config import load_config
from backtranslate.database.connection import init_db

from backtranslate.ui.main_window import MainWindow
from backtranslate.ui.learn_page import LearnPage
from backtranslate.ui.review_page import ReviewPage
from backtranslate.ui.expressions_page import ExpressionsPage
from backtranslate.ui.settings_page import SettingsPage

from backtranslate.ai.worker import EvaluationWorker, EvaluationThread
from backtranslate.database.operations import (
    update_evaluation_status, get_subtitles_for_session,
)


class App:
    def __init__(self):
        self.window = MainWindow()
        self.pages_ready = False
        self.worker = None
        self.eval_thread = None
        self._setup_pages()
        self._setup_worker()

    def _setup_pages(self):
        self.learn_page = LearnPage()
        self.review_page = ReviewPage()
        self.expressions_page = ExpressionsPage()
        self.settings_page = SettingsPage()

        self.window.set_learn_page(self.learn_page)
        self.window.set_review_page(self.review_page)
        self.window.set_expressions_page(self.expressions_page)
        self.window.set_settings_page(self.settings_page)

        # Connections
        self.learn_page.translation_submitted.connect(self._on_translation_submitted)
        self.review_page.redo_submitted.connect(self._on_redo_submitted)
        self.review_page.retry_requested.connect(self._on_retry_requested)

    def _setup_worker(self):
        cfg = load_config()
        self.worker = EvaluationWorker(
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            model=cfg["model"],
            prompt_template=cfg["prompt_template"],
        )
        self.worker.evaluation_done.connect(self._on_eval_done)
        self.worker.evaluation_failed.connect(self._on_eval_failed)

        self.eval_thread = EvaluationThread(self.worker)
        self.eval_thread.task_ready.connect(self.worker.process_next)
        self.eval_thread.start()

    def _build_context(self, sub_row, session_id):
        """Build context string with N previous and N next subtitles."""
        cfg = load_config()
        n = cfg.get("context_n", 1)
        if n == 0:
            return ""
        all_subs = get_subtitles_for_session(session_id)
        current_idx = sub_row["idx"]
        parts = []
        for s in all_subs:
            if s["idx"] < current_idx and s["idx"] >= current_idx - n:
                parts.append(f"Previous: {s['chinese']} -> {s['english_official']}")
            elif s["idx"] > current_idx and s["idx"] <= current_idx + n:
                parts.append(f"Next: {s['chinese']} -> {s['english_official']}")
        return "\n".join(parts)

    def _find_subtitle(self, subtitle_id):
        subs = get_subtitles_for_session(self.learn_page.session_id or 0)
        for s in subs:
            if s["id"] == subtitle_id:
                return s
        return None

    def _on_translation_submitted(self, eval_id, subtitle_id, user_input, official):
        if eval_id == -1:  # session ended
            self._load_review()
            self.window.navigate_to_review()
            return

        # Update worker config (may have changed in settings)
        cfg = load_config()
        self.worker.base_url = cfg["base_url"]
        self.worker.api_key = cfg["api_key"]
        self.worker.model = cfg["model"]
        self.worker.prompt_template = cfg["prompt_template"]

        sub_row = self._find_subtitle(subtitle_id)
        context = self._build_context(sub_row, self.learn_page.session_id) if sub_row else ""

        self.worker.add_task(eval_id, 0, user_input, official, context)

    def _on_redo_submitted(self, eval_id, subtitle_id, user_input, official):
        self._on_translation_submitted(eval_id, subtitle_id, user_input, official)

    def _on_retry_requested(self, eval_id, subtitle_id, user_input, official):
        sub_row = self._find_subtitle(subtitle_id)
        context = self._build_context(sub_row, self.learn_page.session_id) if sub_row else ""
        self.worker.add_task(eval_id, 0, user_input, official, context)

    def _on_eval_done(self, eval_id, result):
        update_evaluation_status(
            eval_id, "done",
            result["meaning_score"],
            result["grammar_score"],
            result["naturalness_score"],
            result["subtitle_style_score"],
            result["analysis"],
            json.dumps(result.get("suggested_expressions", [])),
        )
        # Refresh review page if visible
        if hasattr(self, 'review_page') and self.review_page.session_id:
            # We need to know the subtitle_id; get it from eval
            from backtranslate.database.connection import get_connection
            conn = get_connection()
            row = conn.execute(
                "SELECT t.subtitle_id FROM translations t "
                "JOIN evaluations e ON e.translation_id = t.id "
                "WHERE e.id = ?", (eval_id,)
            ).fetchone()
            conn.close()
            if row:
                self.review_page.update_evaluation(row[0])

    def _on_eval_failed(self, eval_id):
        update_evaluation_status(eval_id, "failed", error="批改失败")

    def _load_review(self):
        if self.learn_page.session_id:
            self.review_page.load_session(self.learn_page.session_id)

    def run(self):
        self.window.show()


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    application = App()
    application.run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify import**

Run: `python -c "from backtranslate.main import main; print('OK')"`
Expected: `OK` (window may briefly open)

- [ ] **Step 3: Commit**

```bash
git add backtranslate/main.py
git commit -m "feat: integrate all pages with AI worker and database"
```

---

### Task 14: Requirements File & Final Verification

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create `requirements.txt`**

```
PySide6>=6.5.0
requests>=2.28.0
pytest>=7.0.0
pytest-qt>=4.2.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: all 19 tests PASS

- [ ] **Step 4: Quick smoke test — launch app**

Run: `python -c "from backtranslate.main import main; main()"`  
Expected: Window opens with sidebar navigation, all 4 pages accessible

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: add requirements.txt"
```
