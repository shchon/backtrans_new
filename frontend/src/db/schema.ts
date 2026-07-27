export const CREATE_TABLES_SQL = `
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total_sentences INTEGER NOT NULL DEFAULT 0,
    completed_sentences INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS subtitles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    idx INTEGER NOT NULL,
    chinese TEXT NOT NULL,
    english_official TEXT NOT NULL DEFAULT '',
    prev_chinese TEXT NOT NULL DEFAULT '',
    prev_english TEXT NOT NULL DEFAULT '',
    next_chinese TEXT NOT NULL DEFAULT '',
    next_english TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtitle_id INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    user_input TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (subtitle_id) REFERENCES subtitles(id)
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    meaning_score INTEGER,
    grammar_score INTEGER,
    naturalness_score INTEGER,
    subtitle_style_score INTEGER,
    analysis_text TEXT,
    suggested_expressions TEXT DEFAULT '[]',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (translation_id) REFERENCES translations(id)
);

CREATE TABLE IF NOT EXISTS expressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase TEXT NOT NULL,
    source_subtitle_id INTEGER,
    notes TEXT NOT NULL DEFAULT '',
    collected_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS self_ratings (
    subtitle_id INTEGER PRIMARY KEY,
    rating INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    subtitle_id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS streak_log (
    date TEXT PRIMARY KEY,
    sentences_completed INTEGER NOT NULL DEFAULT 0
);
`;
