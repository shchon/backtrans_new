# Step 3: AI 接入 + 完整前端页面 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成 AI 异步调用 + 全部 5 个前端页面（学习、复盘、收藏夹、表达库、设置）

**Architecture:** FastAPI 后台线程调 AI，前端轮询结果。React state 切换 5 个页面。

**Tech Stack:** FastAPI + threading / React + TypeScript / PySide6 (existing)

---

### Task 1: 后端 — AI + 配置 API 端点

**Files:**
- Modify: `backend/api.py`
- Modify: `backend/schemas.py`

- [ ] **Add AI evaluation + config schemas** to `backend/schemas.py`:

```python
class TranslateRequest(BaseModel):
    subtitle_id: int
    user_input: str

class TranslateResponse(BaseModel):
    translation_id: int
    eval_id: int
    status: str  # pending

class EvaluationStatus(BaseModel):
    id: int
    status: str  # pending | done | failed
    meaning_score: Optional[int] = None
    grammar_score: Optional[int] = None
    naturalness_score: Optional[int] = None
    subtitle_style_score: Optional[int] = None
    analysis_text: Optional[str] = None
    suggested_expressions: list[str] = []
    error_message: Optional[str] = None

class EvaluationListResponse(BaseModel):
    evaluations: list[EvaluationStatus]

class ConfigResponse(BaseModel):
    base_url: str
    api_key: str
    model: str
    context_n: int
    font_size: int
    prompt_template: str

class ConfigUpdateRequest(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    context_n: Optional[int] = None
    font_size: Optional[int] = None
    prompt_template: Optional[str] = None
```

- [ ] **Add AI evaluation + config endpoints** to `backend/api.py`:

Add imports at top:
```python
import json
import threading
from datetime import datetime
from backtranslate.database.connection import get_connection
from backtranslate.database import operations as db
from backtranslate.ai.client import call_ai
from backtranslate.models import AppSettings
```

Add background AI function:
```python
def _run_ai_eval(eval_id: int, translation_id: int, subtitle_id: int,
                 session_id: int, user_input: str, official: str):
    """Run AI evaluation in background thread."""
    try:
        conn = get_connection()
        # Get config
        from backtranslate.config import load_config
        cfg = load_config()
        conn.close()

        # Build context
        subs_rows = db.get_subtitles_for_session(session_id)
        # Find current subtitle
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

        result = call_ai(
            cfg["base_url"], cfg["api_key"], cfg["model"],
            cfg["prompt_template"], context, user_input, official,
        )
        if result is not None:
            suggested = json.dumps(result.get("suggested_expressions", []))
            db.update_evaluation_status(
                eval_id, "done",
                result["meaning_score"], result["grammar_score"],
                result["naturalness_score"], result["subtitle_style_score"],
                result["analysis"], suggested,
            )
        else:
            db.update_evaluation_status(eval_id, "failed", error="AI call returned None")
    except Exception as e:
        try:
            db.update_evaluation_status(eval_id, "failed", error=str(e))
        except Exception:
            pass
```

Add endpoints (inside the existing router):
```python
@router.post("/sessions/{session_id}/translate", response_model=TranslateResponse)
def submit_translation(session_id: int, req: TranslateRequest):
    conn = get_connection()
    # Create translation
    tid = db.create_translation(req.subtitle_id, req.user_input, version=1)
    # Create evaluation
    eid = db.create_evaluation(tid, status="pending")
    conn.close()

    # Get official subtitle text
    subs = db.get_subtitles_for_session(session_id)
    official = ""
    for s in subs:
        if s["id"] == req.subtitle_id:
            official = s["english_official"]
            break

    # Launch AI in background
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
        suggested_expressions=suggested,
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
            suggested_expressions=suggested,
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
    for field in req.model_dump(exclude_none=True):
        cfg[field] = getattr(req, field)
    save_config(cfg)
    return ConfigResponse(**cfg)
```

- [ ] **Verify** the backend starts:
```powershell
cd i:\python\backtranslatess
python -c "from backend.api import router; print('OK')"
```

---

### Task 2: 后端 — SRT 导入 + 收藏 + 表达 API 端点

**Files:**
- Modify: `backend/api.py`
- Modify: `backend/schemas.py`

- [ ] **Add SRT import + expression + favorite schemas** to `backend/schemas.py`:

```python
class SrtImportRequest(BaseModel):
    chinese_srt: str
    english_srt: str
    use_timecode: bool = False
    name: str = ""

class SrtImportResponse(BaseModel):
    session: SessionResponse
    subtitles: list[SubtitleItem]

class SessionCreateResponse(BaseModel):
    session: SessionResponse
    subtitles: list[SubtitleItem]

class ExpressionCreateRequest(BaseModel):
    phrase: str
    subtitle_id: int = 0

class ExpressionResponse(BaseModel):
    id: int
    phrase: str
    notes: str = ""

class ExpressionListResponse(BaseModel):
    expressions: list[ExpressionResponse]

class FavoriteItem(BaseModel):
    id: int  # subtitle_id
    idx: int
    chinese: str
    english_official: str
```

- [ ] **Add SRT import + expression + favorite endpoints** to `backend/api.py`:

```python
@router.post("/sessions/import", response_model=SrtImportResponse)
def import_srt(req: SrtImportRequest):
    from backtranslate.srt.parser import parse_srt
    from backtranslate.srt.pairing import pair_by_index, pair_by_timecode

    ch_subs = parse_srt(req.chinese_srt)
    en_subs = parse_srt(req.english_srt)
    if not ch_subs or not en_subs:
        raise HTTPException(status_code=400, detail="Empty SRT content")

    if req.use_timecode:
        pairs = pair_by_timecode(ch_subs, en_subs)
    else:
        pairs = pair_by_index(ch_subs, en_subs)

    if not pairs:
        raise HTTPException(status_code=400, detail="No matching subtitle pairs found")

    from backtranslate.database.connection import init_db
    init_db()

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

    session_row = db.get_session(session_id)
    return SrtImportResponse(
        session=SessionResponse(**dict(session_row)),
        subtitles=[SubtitleItem(**s) for s in subtitles],
    )

@router.post("/sessions/{session_id}/complete")
def complete_session(session_id: int):
    session = _session_service.get(session_id)
    if session is None:
        raise HTTPException(status_code=404)
    db.update_session_completed(session_id, session.total_sentences)
    db.record_sentence_completed()
    return {"status": "completed"}


@router.get("/expressions", response_model=ExpressionListResponse)
def list_expressions():
    rows = db.get_all_expressions()
    return ExpressionListResponse(
        expressions=[ExpressionResponse(**r) for r in rows]
    )

@router.post("/expressions", response_model=ExpressionResponse)
def create_expression(req: ExpressionCreateRequest):
    eid = db.add_expression(req.phrase, req.subtitle_id)
    return ExpressionResponse(id=eid, phrase=req.phrase)

@router.delete("/expressions/{expr_id}")
def delete_expression(expr_id: int):
    db.delete_expression(expr_id)
    return {"status": "deleted"}


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
```

- [ ] **Verify imports**:
```powershell
python -c "from backend.api import router; print('OK')"
```

---

### Task 3: 前端 — 更新 types + API client + 导航

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/FavoritesPage.tsx`
- Create: `frontend/src/pages/ExpressionsPage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Update `frontend/src/types.ts`** — add all new types:

```typescript
export interface TranslateRequest {
  subtitle_id: number;
  user_input: string;
}

export interface TranslateResponse {
  translation_id: number;
  eval_id: number;
  status: string;
}

export interface EvaluationStatus {
  id: number;
  status: string;  // pending | done | failed
  meaning_score: number | null;
  grammar_score: number | null;
  naturalness_score: number | null;
  subtitle_style_score: number | null;
  analysis_text: string | null;
  suggested_expressions: string[];
  error_message: string | null;
}

export interface SrtImportRequest {
  chinese_srt: string;
  english_srt: string;
  use_timecode: boolean;
  name: string;
}

export interface SrtImportResponse {
  session: Session;
  subtitles: SubtitleItem[];
}

export interface EvaluationListResponse {
  evaluations: EvaluationStatus[];
}

export interface ConfigData {
  base_url: string;
  api_key: string;
  model: string;
  context_n: number;
  font_size: number;
  prompt_template: string;
}

export interface ExpressionItem {
  id: number;
  phrase: string;
  notes?: string;
}

export interface FavoriteItem {
  id: number;
  idx: number;
  chinese: string;
  english_official: string;
  // plus other fields from the joined query
  [key: string]: unknown;
}
```

- [ ] **Update `frontend/src/api/client.ts`** — add all new API methods:

```typescript
export async function importSrt(req: SrtImportRequest): Promise<SrtImportResponse> {
  const res = await fetch(`${API_BASE}/sessions/import`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Import failed: ${res.status}`);
  return res.json();
}

export async function submitTranslation(sessionId: number, req: TranslateRequest): Promise<TranslateResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/translate`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  return res.json();
}

export async function getEvaluation(evalId: number): Promise<EvaluationStatus> {
  return fetchJson<EvaluationStatus>(`${API_BASE}/evaluations/${evalId}`);
}

export async function getSessionEvaluations(sessionId: number): Promise<EvaluationListResponse> {
  return fetchJson<EvaluationListResponse>(`${API_BASE}/sessions/${sessionId}/evaluations`);
}

export async function retryEvaluation(evalId: number): Promise<void> {
  await fetch(`${API_BASE}/evaluations/${evalId}/retry`, {method: 'POST'});
}

export async function completeSession(sessionId: number): Promise<void> {
  await fetch(`${API_BASE}/sessions/${sessionId}/complete`, {method: 'POST'});
}

export async function getConfig(): Promise<ConfigData> {
  return fetchJson<ConfigData>(`${API_BASE}/config`);
}

export async function updateConfig(cfg: Partial<ConfigData>): Promise<ConfigData> {
  const res = await fetch(`${API_BASE}/config`, {
    method: 'PUT', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(cfg),
  });
  return res.json();
}

export async function getExpressions(): Promise<{expressions: ExpressionItem[]}> {
  return fetchJson(`${API_BASE}/expressions`);
}

export async function addExpression(phrase: string, subtitleId?: number): Promise<ExpressionItem> {
  const res = await fetch(`${API_BASE}/expressions`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({phrase, subtitle_id: subtitleId ?? 0}),
  });
  return res.json();
}

export async function deleteExpression(exprId: number): Promise<void> {
  await fetch(`${API_BASE}/expressions/${exprId}`, {method: 'DELETE'});
}

export async function getFavorites(): Promise<FavoriteItem[]> {
  return fetchJson(`${API_BASE}/favorites`);
}

export async function addFavorite(subtitleId: number): Promise<void> {
  await fetch(`${API_BASE}/favorites/${subtitleId}`, {method: 'POST'});
}

export async function removeFavorite(subtitleId: number): Promise<void> {
  await fetch(`${API_BASE}/favorites/${subtitleId}`, {method: 'DELETE'});
}
```

- [ ] **Update `App.tsx`** — full sidebar navigation with all 5 pages:

```tsx
import { useState } from 'react';
import LearnPage from './pages/LearnPage';
import ReviewPage from './pages/ReviewPage';
import FavoritesPage from './pages/FavoritesPage';
import ExpressionsPage from './pages/ExpressionsPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

type Page = 'learn' | 'review' | 'favorites' | 'expressions' | 'settings';

const NAV_ITEMS: {key: Page; label: string}[] = [
  {key: 'learn', label: '学习'},
  {key: 'review', label: '复盘'},
  {key: 'favorites', label: '收藏夹'},
  {key: 'expressions', label: '表达库'},
  {key: 'settings', label: '设置'},
];

export default function App() {
  const [page, setPage] = useState<Page>('learn');
  const [reviewSessionId, setReviewSessionId] = useState<number | null>(null);

  return (
    <div className="app-layout">
      <nav className="sidebar">
        {NAV_ITEMS.map(item => (
          <button
            key={item.key}
            className={`nav-btn ${page === item.key ? 'active' : ''}`}
            onClick={() => setPage(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <main className="content">
        {page === 'learn' && <LearnPage onNavigateToReview={(sid) => { setReviewSessionId(sid); setPage('review'); }} />}
        {page === 'review' && <ReviewPage sessionId={reviewSessionId} />}
        {page === 'favorites' && <FavoritesPage onStartReview={(sid) => { setReviewSessionId(sid); setPage('review'); }} />}
        {page === 'expressions' && <ExpressionsPage />}
        {page === 'settings' && <SettingsPage />}
      </main>
    </div>
  );
}
```

- [ ] **Update `App.css`** — add sidebar layout:

```css
.app-layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 180px;
  background: #f5f5f5;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.nav-btn {
  text-align: left;
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
  background: transparent;
  cursor: pointer;
}
.nav-btn:hover { background: #e8e8e8; }
.nav-btn.active { background: #d0e0ff; font-weight: bold; }

.content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}
```

---

### Task 4: 前端 — LearnPage（完整 Sprint 模式）

**Files:**
- Create/Modify: `frontend/src/pages/LearnPage.tsx`

Complete LearnPage with:
- Import button → file input for Chinese and English SRT files
- Sprint mode: show one Chinese sentence at a time
- Input field + submit (Enter or button)
- Skip button
- Progress bar + stats display
- Poll for AI result after each submission
- After all sentences done: auto-navigate to review

Key state:
```typescript
const [sessionId, setSessionId] = useState<number | null>(null);
const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
const [currentIdx, setCurrentIdx] = useState(0);
const [completedCount, setCompletedCount] = useState(0);
const [loadingEval, setLoadingEval] = useState(false);
const [stats, setStats] = useState<Stats | null>(null);
```

Import flow:
1. Click import → open file input for Chinese SRT → read file content
2. Open file input for English SRT → read file content
3. Call `importSrt()` API
4. Start sprint mode

Polling logic after submit:
1. Call `submitTranslation(sessionId, {subtitle_id, user_input})` → get `{eval_id}`
2. `setInterval` every 1s: `getEvaluation(eval_id)`
3. When status === "done" or timeout (30s): stop polling, move to next sentence

---

### Task 5: 前端 — ReviewPage

**Files:**
- Create: `frontend/src/pages/ReviewPage.tsx`

ReviewPage shows evaluation results for a session. Key features:
- Load evaluations from API on mount
- List cards with score summary
- Expand/collapse detail
- Star toggle for favorites
- Redo translation button
- Collect expressions

---

### Task 6: 前端 — FavoritesPage + ExpressionsPage + SettingsPage

**Files:**
- Create: `frontend/src/pages/FavoritesPage.tsx`
- Create: `frontend/src/pages/ExpressionsPage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`

Each page is a simple list view with API CRUD operations.
SettingsPage has the AI configuration form + test connection button.

---

### Task 7: 集成测试

- Start backend + frontend
- Test the full flow: import SRT → translate → AI evaluates → review results
- Verify all 5 pages render correctly
