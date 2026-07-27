import sqlite3
from datetime import datetime, timedelta

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
    conn.row_factory = sqlite3.Row
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
                session_id, sub["idx"], sub["chinese"], sub["english_official"],
                sub.get("prev_chinese", ""), sub.get("prev_english", ""),
                sub.get("next_chinese", ""), sub.get("next_english", ""),
            ),
        )
    conn.commit()
    conn.close()


def get_subtitles_for_session(session_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
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
    conn.row_factory = sqlite3.Row
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
        (status, meaning, grammar, naturalness, subtitle_style,
         analysis, suggested, error, eval_id),
    )
    conn.commit()
    conn.close()


def get_evaluation_for_translation(translation_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
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
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM expressions ORDER BY collected_at DESC"
    ).fetchall()
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
    conn.row_factory = sqlite3.Row
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


# ---------- favorites ----------

def add_favorite(subtitle_id):
    conn = get_connection()
    cur = conn.execute(
        "INSERT OR IGNORE INTO favorites (subtitle_id) VALUES (?)",
        (subtitle_id,),
    )
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return fid


def remove_favorite(subtitle_id):
    conn = get_connection()
    conn.execute("DELETE FROM favorites WHERE subtitle_id = ?", (subtitle_id,))
    conn.commit()
    conn.close()


def clear_favorites():
    conn = get_connection()
    conn.execute("DELETE FROM favorites")
    conn.commit()
    conn.close()


def get_favorites():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT f.id as fav_id, f.created_at as fav_created_at,
                  s.id, s.session_id, s.idx, s.chinese, s.english_official,
                  s.prev_chinese, s.prev_english, s.next_chinese, s.next_english
           FROM favorites f
           JOIN subtitles s ON f.subtitle_id = s.id
           ORDER BY f.created_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_favorite(subtitle_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM favorites WHERE subtitle_id = ?", (subtitle_id,)
    ).fetchone()
    conn.close()
    return row is not None


# ---------- learning stats ----------

def record_sentence_completed():
    """Increment today's completed sentence count."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute(
        """INSERT INTO streak_log (date, sentences_completed) VALUES (?, 1)
           ON CONFLICT(date) DO UPDATE SET sentences_completed = sentences_completed + 1""",
        (today,),
    )
    conn.commit()
    conn.close()


def get_today_stats():
    """Return today's sentence count."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    row = conn.execute(
        "SELECT sentences_completed FROM streak_log WHERE date = ?", (today,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_total_sentences():
    """Return total sentences completed across all time."""
    conn = get_connection()
    row = conn.execute("SELECT COALESCE(SUM(sentences_completed), 0) FROM streak_log").fetchone()
    conn.close()
    return row[0]


def get_streak_days():
    """Calculate consecutive days with practice (including today if any)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT date FROM streak_log WHERE sentences_completed > 0 ORDER BY date DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return 0

    streak = 0
    today = datetime.now().date()
    # Check if today has practice
    today_str = today.strftime("%Y-%m-%d")
    if rows[0][0] != today_str:
        # No practice today, check if yesterday had practice
        yesterday = today - timedelta(days=1)
        if rows[0][0] != yesterday.strftime("%Y-%m-%d"):
            return 0

    for i, (date_str,) in enumerate(rows):
        expected = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if date_str == expected:
            streak += 1
        else:
            break

    return streak


def get_all_stats():
    """Return all stats as a dict."""
    return {
        "today": get_today_stats(),
        "total": get_total_sentences(),
        "streak": get_streak_days(),
    }
