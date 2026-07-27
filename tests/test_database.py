import pytest
from backtranslate.database.connection import init_db, get_connection
from backtranslate.database.operations import (
    create_session, create_subtitles_batch, get_session,
    get_subtitles_for_session, create_translation,
    get_latest_translation, get_all_translations_for_subtitle,
    create_evaluation, update_evaluation_status,
    get_evaluation_for_translation, add_expression,
    get_all_expressions, delete_expression,
    upsert_self_rating, get_self_rating, clear_session_data,
)


@pytest.fixture
def db():
    init_db()
    conn = get_connection()
    # Clear all data so tests are isolated from previous runs
    conn.execute("DELETE FROM self_ratings")
    conn.execute("DELETE FROM evaluations")
    conn.execute("DELETE FROM translations")
    conn.execute("DELETE FROM subtitles")
    conn.execute("DELETE FROM expressions")
    conn.execute("DELETE FROM sessions")
    conn.commit()
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
