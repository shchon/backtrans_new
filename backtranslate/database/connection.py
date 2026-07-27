import sqlite3
import os
from backtranslate._paths import get_data_dir

DB_DIR = get_data_dir()
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

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtitle_id INTEGER NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subtitle_id) REFERENCES subtitles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    sentence_count INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS streak_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    sentences_completed INTEGER DEFAULT 0
);
"""


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
