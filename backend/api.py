import json
import sqlite3
import threading
from fastapi import APIRouter, HTTPException
from backtranslate.database.connection import get_connection
from backtranslate.database import operations as db
from backtranslate.services import SessionService, SubtitleService, StatsService
from .schemas import (
    SessionResponse, SessionListResponse,
    SubtitleItem, SubtitleListResponse, StatsResponse,
    TranslateRequest, TranslateResponse,
    EvaluationStatus, EvaluationListResponse,
    ConfigResponse, ConfigUpdateRequest,
    SrtImportRequest, SrtImportResponse,
    ExpressionCreateRequest, ExpressionItem, ExpressionListResponse,
)

router = APIRouter(prefix="/api")

_session_service = SessionService()
_subtitle_service = SubtitleService()
_stats_service = StatsService()


def _run_ai_eval(eval_id: int, translation_id: int, subtitle_id: int,
                 session_id: int, user_input: str, official: str):
    """Run AI evaluation in background thread."""
    try:
        from backtranslate.config import load_config
        cfg = load_config()

        # Build context
        subs_rows = db.get_subtitles_for_session(session_id)
        current = None
        for s in subs_rows:
            if s["id"] == subtitle_id:
                current = s
                break
        if not current:
            db.update_evaluation_status(eval_id, "failed", error="subtitle not found")
            return

        n = cfg.get("context_n", 1)
        context_parts = []
        for s in subs_rows:
            if s["idx"] < current["idx"] and s["idx"] >= current["idx"] - n:
                context_parts.append(f"前一句: {s['chinese']}")
            elif s["idx"] > current["idx"] and s["idx"] <= current["idx"] + n:
                context_parts.append(f"后一句: {s['chinese']}")
        context = ""
        if context_parts:
            context = "上下文（仅供参考，不参与评分）:\n" + "\n".join(context_parts)

        from backtranslate.ai.client import call_ai
        result = call_ai(
            cfg["base_url"], cfg["api_key"], cfg["model"],
            cfg["prompt_template"], context, user_input, official,
        )
        if result is not None:
            suggested = json.dumps(result.get("suggested_expressions", []))
            db.update_evaluation_status(
                eval_id, "done",
                result.get("meaning_score"), result.get("grammar_score"),
                result.get("naturalness_score"), result.get("subtitle_style_score"),
                result.get("analysis"), suggested,
            )
        else:
            db.update_evaluation_status(eval_id, "failed", error="AI call returned None")
    except Exception as e:
        try:
            db.update_evaluation_status(eval_id, "failed", error=str(e))
        except Exception:
            pass


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return SessionListResponse(
        sessions=[SessionResponse(**dict(r)) for r in rows]
    )


@router.get("/sessions/{session_id}/subtitles", response_model=SubtitleListResponse)
def get_session_subtitles(session_id: int):
    session = _session_service.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    subtitles = _subtitle_service.get_by_session(session_id)
    return SubtitleListResponse(
        subtitles=[SubtitleItem(
            id=s.id, idx=s.idx, chinese=s.chinese,
            english_official=s.english_official,
            prev_chinese=s.prev_chinese, prev_english=s.prev_english,
            next_chinese=s.next_chinese, next_english=s.next_english,
        ) for s in subtitles],
        session=SessionResponse(
            id=session.id, name=session.name,
            total_sentences=session.total_sentences,
            completed_sentences=session.completed_sentences,
            created_at=session.created_at,
        ),
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    stats = _stats_service.get_all()
    return StatsResponse(**stats)


@router.post("/sessions/{session_id}/translate", response_model=TranslateResponse)
def submit_translation(session_id: int, req: TranslateRequest):
    tid = db.create_translation(req.subtitle_id, req.user_input, 1)
    eid = db.create_evaluation(tid, "pending")

    subs = db.get_subtitles_for_session(session_id)
    official = ""
    for s in subs:
        if s["id"] == req.subtitle_id:
            official = s["english_official"]
            break

    thread = threading.Thread(
        target=_run_ai_eval,
        args=(eid, tid, req.subtitle_id, session_id, req.user_input, official),
        daemon=True,
    )
    thread.start()

    return TranslateResponse(translation_id=tid, eval_id=eid, status="pending")


@router.get("/evaluations/{eval_id}", response_model=EvaluationStatus)
def get_evaluation(eval_id: int):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    d = dict(row)
    suggested = d.get("suggested_expressions", "")
    if isinstance(suggested, str):
        try:
            suggested = json.loads(suggested) if suggested else []
        except (json.JSONDecodeError, TypeError):
            suggested = []
    return EvaluationStatus(
        id=d["id"], status=d["status"],
        meaning_score=d.get("meaning_score"),
        grammar_score=d.get("grammar_score"),
        naturalness_score=d.get("naturalness_score"),
        subtitle_style_score=d.get("subtitle_style_score"),
        analysis_text=d.get("analysis_text"),
        suggested_expressions=suggested if isinstance(suggested, list) else [],
        error_message=d.get("error_message"),
    )


@router.get("/sessions/{session_id}/evaluations", response_model=EvaluationListResponse)
def list_evaluations(session_id: int):
    rows = db.get_evaluations_for_session(session_id)
    evals = []
    for d in rows:
        suggested = d.get("suggested_expressions", "")
        if isinstance(suggested, str):
            try:
                suggested = json.loads(suggested) if suggested else []
            except (json.JSONDecodeError, TypeError):
                suggested = []
        evals.append(EvaluationStatus(
            id=d["id"], status=d["status"],
            meaning_score=d.get("meaning_score"),
            grammar_score=d.get("grammar_score"),
            naturalness_score=d.get("naturalness_score"),
            subtitle_style_score=d.get("subtitle_style_score"),
            analysis_text=d.get("analysis_text"),
            suggested_expressions=suggested if isinstance(suggested, list) else [],
        ))
    return EvaluationListResponse(evaluations=evals)


@router.post("/evaluations/{eval_id}/retry")
def retry_evaluation(eval_id: int):
    db.update_evaluation_status(eval_id, "pending")
    return {"status": "retrying"}


@router.get("/config", response_model=ConfigResponse)
def get_config():
    from backtranslate.config import load_config
    cfg = load_config()
    return ConfigResponse(**cfg)


@router.put("/config", response_model=ConfigResponse)
def update_config(req: ConfigUpdateRequest):
    from backtranslate.config import load_config, save_config
    cfg = load_config()
    for field, val in req.model_dump(exclude_none=True).items():
        cfg[field] = val
    save_config(cfg)
    return ConfigResponse(**cfg)


# ===== SRT Import =====

@router.post("/sessions/import", response_model=SrtImportResponse)
def import_srt(req: SrtImportRequest):
    from backtranslate.srt.parser import parse_srt
    from backtranslate.srt.pairing import pair_by_index, pair_by_timecode
    from backtranslate.database.connection import init_db

    init_db()
    ch_subs = parse_srt(req.chinese_srt)
    en_subs = parse_srt(req.english_srt)
    if not ch_subs or not en_subs:
        raise HTTPException(status_code=400, detail="Empty SRT content")

    if req.use_timecode:
        pairs = pair_by_timecode(ch_subs, en_subs)
    else:
        pairs = pair_by_index(ch_subs, en_subs)
    if not pairs:
        raise HTTPException(status_code=400, detail="No matching subtitle pairs")

    name = req.name or ch_subs[0].get("name", "未命名")
    session_id = db.create_session(name, len(pairs))

    subtitles = []
    for i, (ch, en) in enumerate(pairs):
        prev_ch = pairs[i - 1][0]["text"] if i > 0 else ""
        prev_en = pairs[i - 1][1]["text"] if i > 0 else ""
        next_ch = pairs[i + 1][0]["text"] if i < len(pairs) - 1 else ""
        next_en = pairs[i + 1][1]["text"] if i < len(pairs) - 1 else ""
        subtitles.append({
            "idx": i + 1, "chinese": ch["text"], "english_official": en["text"],
            "prev_chinese": prev_ch, "prev_english": prev_en,
            "next_chinese": next_ch, "next_english": next_en,
        })

    db.create_subtitles_batch(session_id, subtitles)

    # Re-read from DB to get auto-generated IDs
    db_subs = db.get_subtitles_for_session(session_id)
    session_row = db.get_session(session_id)
    return SrtImportResponse(
        session=SessionResponse(**dict(session_row)),
        subtitles=[SubtitleItem(**dict(s)) for s in db_subs],
    )


@router.post("/sessions/{session_id}/complete")
def complete_session(session_id: int):
    session = _session_service.get(session_id)
    if session is None:
        raise HTTPException(status_code=404)
    db.update_session_completed(session_id, session.total_sentences)
    db.record_sentence_completed()
    return {"status": "completed"}


# ===== Expressions =====

@router.get("/expressions", response_model=ExpressionListResponse)
def list_expressions():
    rows = db.get_all_expressions()
    return ExpressionListResponse(
        expressions=[ExpressionItem(**r) for r in rows]
    )

@router.post("/expressions", response_model=ExpressionItem)
def create_expression(req: ExpressionCreateRequest):
    eid = db.add_expression(req.phrase, req.subtitle_id)
    return ExpressionItem(id=eid, phrase=req.phrase, source_subtitle_id=req.subtitle_id)

@router.delete("/expressions/{expr_id}")
def delete_expression(expr_id: int):
    db.delete_expression(expr_id)
    return {"status": "deleted"}


# ===== Favorites =====

@router.get("/favorites")
def list_favorites():
    return db.get_favorites()

@router.post("/favorites/{subtitle_id}")
def add_favorite(subtitle_id: int):
    db.add_favorite(subtitle_id)
    return {"status": "added"}

@router.delete("/favorites/{subtitle_id}")
def remove_favorite(subtitle_id: int):
    db.remove_favorite(subtitle_id)
    return {"status": "removed"}
