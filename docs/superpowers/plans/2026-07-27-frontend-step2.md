# Step 2: FastAPI + React 前端 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 FastAPI 后端提供 REST API + React 前端显示字幕列表。

**Architecture:** FastAPI 直接复用 Phase 1 的 `backtranslate/services/` 层。React (Vite + TypeScript) 通过 HTTP 调用后端。

**Tech Stack:** Python FastAPI + Pydantic v2 / Vite + React 19 + TypeScript

---

### Task 1: FastAPI 后端 — API 路由

**Files:**
- Create: `backend/schemas.py`
- Create: `backend/api.py`
- Create: `backend/main.py`

- [ ] **Step 1: 创建 Pydantic schemas**

`backend/schemas.py`:
```python
from pydantic import BaseModel
from typing import Optional


class SessionResponse(BaseModel):
    id: int
    name: str
    total_sentences: int
    completed_sentences: int
    created_at: str


class SubtitleItem(BaseModel):
    id: int
    idx: int
    chinese: str
    english_official: str
    prev_chinese: str = ""
    prev_english: str = ""
    next_chinese: str = ""
    next_english: str = ""


class StatsResponse(BaseModel):
    today: int
    total: int
    streak: int


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class SubtitleListResponse(BaseModel):
    subtitles: list[SubtitleItem]
    session: Optional[SessionResponse] = None
```

- [ ] **Step 2: 创建 API 路由**

`backend/api.py`:
```python
from fastapi import APIRouter, HTTPException
from backtranslate.database.connection import get_connection
from backtranslate.services import (
    SessionService, SubtitleService, StatsService,
)
from .schemas import (
    SessionResponse, SessionListResponse,
    SubtitleItem, SubtitleListResponse,
    StatsResponse,
)

router = APIRouter(prefix="/api")

# Instantiate services
_session_service = SessionService()
_subtitle_service = SubtitleService()
_stats_service = StatsService()


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions():
    """List all learning sessions."""
    rows = _session_service.get_connection()
    # Use raw query since SessionService only has get() by id
    conn = get_connection()
    conn.row_factory = None  # use sqlite3.Row from get_connection already
    # Actually let's use session_service properly
    # For now, query all sessions directly
    import sqlite3
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
    """Get subtitles for a session."""
    session_row = _session_service.get(session_id)
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    subtitles = _subtitle_service.get_by_session(session_id)
    return SubtitleListResponse(
        subtitles=[SubtitleItem(
            id=s.id, idx=s.idx,
            chinese=s.chinese, english_official=s.english_official,
            prev_chinese=s.prev_chinese, prev_english=s.prev_english,
            next_chinese=s.next_chinese, next_english=s.next_english,
        ) for s in subtitles],
        session=SessionResponse(
            id=session_row.id, name=session_row.name,
            total_sentences=session_row.total_sentences,
            completed_sentences=session_row.completed_sentences,
            created_at=session_row.created_at,
        ),
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    stats = _stats_service.get_all()
    return StatsResponse(**stats)
```

Wait, `SessionService` doesn't have a `get_connection` method or a way to list all sessions. Let me fix this.

Actually looking at my services, `SessionService` has `get(session_id)` but no `list_all()`. I need to either add one or query directly. Let me use direct query for now since this is just the backend API, not a core service concern.

Let me also fix the `_session_service.get()` — it returns `Optional[Session]`, not a dict.

Let me rewrite the api.py properly:

`backend/api.py`:
```python
import sqlite3
from fastapi import APIRouter, HTTPException
from backtranslate.database.connection import get_connection
from backtranslate.services import SessionService, SubtitleService, StatsService
from .schemas import (
    SessionResponse, SessionListResponse,
    SubtitleItem, SubtitleListResponse, StatsResponse,
)

router = APIRouter(prefix="/api")

_session_service = SessionService()
_subtitle_service = SubtitleService()
_stats_service = StatsService()


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
```

OK, this is cleaner.

- [ ] **Step 3: 创建 FastAPI 入口**

`backend/main.py`:
```python
"""FastAPI 后端入口 — 提供 REST API 给前端"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router

app = FastAPI(title="BackTranslate API", version="0.1.0")

# CORS: allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", port=8765, reload=True)
```

- [ ] **Step 4: 验证后端启动并响应**

```powershell
cd i:\python\backtranslatess
python -c "from backend.api import router; print('API router OK')"
python -c "from backend.main import app; print('FastAPI app OK')"
```

Expected: Both print OK

- [ ] **Step 5: 启动后端并测试端点**

```powershell
# Start in background
Start-Process -NoNewWindow -RedirectStandardOutput backend.log python -m "uvicorn" "backend.main:app" "--port" "8765"
Start-Sleep 3
# Test endpoints
curl -s http://localhost:8765/api/sessions
curl -s http://localhost:8765/api/stats
```

Expected: Returns JSON data from the database

- [ ] **Step 6: 停止测试服务器**

```powershell
Stop-Process -Name "python" -Force
```

---

### Task 2: React 前端 — 项目脚手架

**Files:**
- Create: `frontend/` (Vite project scaffold)
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: 用 Vite 创建 React + TypeScript 项目**

```powershell
cd i:\python\backtranslatess
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

This creates the standard Vite + React + TypeScript scaffold with `src/`, `index.html`, `tsconfig.json`, etc.

- [ ] **Step 2: 创建 TypeScript 类型定义**

`frontend/src/types.ts`:
```typescript
export interface Session {
  id: number;
  name: string;
  total_sentences: number;
  completed_sentences: number;
  created_at: string;
}

export interface SubtitleItem {
  id: number;
  idx: number;
  chinese: string;
  english_official: string;
  prev_chinese: string;
  prev_english: string;
  next_chinese: string;
  next_english: string;
}

export interface Stats {
  today: number;
  total: number;
  streak: number;
}

export interface SessionListResponse {
  sessions: Session[];
}

export interface SubtitleListResponse {
  subtitles: SubtitleItem[];
  session: Session | null;
}
```

- [ ] **Step 3: 创建 API 客户端**

`frontend/src/api/client.ts`:
```typescript
import type { SessionListResponse, SubtitleListResponse, Stats } from '../types';

const API_BASE = 'http://localhost:8765/api';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function listSessions(): Promise<SessionListResponse> {
  return fetchJson<SessionListResponse>(`${API_BASE}/sessions`);
}

export async function getSessionSubtitles(sessionId: number): Promise<SubtitleListResponse> {
  return fetchJson<SubtitleListResponse>(`${API_BASE}/sessions/${sessionId}/subtitles`);
}

export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${API_BASE}/stats`);
}
```

---

### Task 3: React 前端 — LearnPage 字幕列表

**Files:**
- Create: `frontend/src/pages/LearnPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: 创建 LearnPage 组件**

`frontend/src/pages/LearnPage.tsx`:
```tsx
import { useState, useEffect } from 'react';
import type { Session, SubtitleItem } from '../types';
import { listSessions, getSessionSubtitles } from '../api/client';

export default function LearnPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSessions()
      .then(data => {
        setSessions(data.sessions);
        if (data.sessions.length > 0) {
          setSelectedSessionId(data.sessions[0].id);
        }
      })
      .catch(err => setError(err.message));
  }, []);

  useEffect(() => {
    if (selectedSessionId === null) return;
    setLoading(true);
    getSessionSubtitles(selectedSessionId)
      .then(data => {
        setSubtitles(data.subtitles);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedSessionId]);

  const currentSession = sessions.find(s => s.id === selectedSessionId);

  return (
    <div className="learn-page">
      <header className="learn-header">
        <h1>回译训练</h1>
        <div className="session-selector">
          <label>学习会话：</label>
          <select
            value={selectedSessionId ?? ''}
            onChange={e => setSelectedSessionId(Number(e.target.value))}
          >
            {sessions.map(s => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.completed_sentences}/{s.total_sentences})
              </option>
            ))}
          </select>
        </div>
      </header>

      {currentSession && (
        <div className="session-info">
          进度：{currentSession.completed_sentences} / {currentSession.total_sentences} 句
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">加载中...</div>
      ) : (
        <div className="subtitle-list">
          {subtitles.map(sub => (
            <div key={sub.id} className="subtitle-row">
              <span className="sub-idx">#{sub.idx}</span>
              <span className="sub-chinese">{sub.chinese}</span>
              <span className="sub-english">{sub.english_official}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 更新 App.tsx**

`frontend/src/App.tsx`:
```tsx
import LearnPage from './pages/LearnPage';
import './App.css';

export default function App() {
  return <LearnPage />;
}
```

- [ ] **Step 3: 更新 App.css**

`frontend/src/App.css`:
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
}

.learn-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.learn-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.learn-header h1 {
  font-size: 20px;
  font-weight: bold;
}

.session-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-selector select {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}

.session-info {
  color: #666;
  margin-bottom: 16px;
  font-size: 14px;
}

.error {
  background: #fdd;
  color: #c33;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}

.loading {
  text-align: center;
  color: #999;
  padding: 40px;
  font-size: 16px;
}

.subtitle-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subtitle-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.subtitle-row:hover {
  border-color: #4a90d9;
}

.sub-idx {
  color: #999;
  font-size: 12px;
  min-width: 30px;
}

.sub-chinese {
  flex: 1;
  font-size: 14px;
}

.sub-english {
  flex: 1;
  font-size: 14px;
  color: #4a90d9;
  font-style: italic;
}
```

- [ ] **Step 4: 验证前端可构建**

```powershell
cd i:\python\backtranslatess\frontend
npm run build
```

Expected: Build succeeds, output in `dist/` directory.

---

### Task 4: 集成测试

- [ ] **Step 1: 分别启动后端和前端**

Terminal 1 (backend):
```powershell
cd i:\python\backtranslatess
python -m uvicorn backend.main:app --port 8765
```

Terminal 2 (frontend):
```powershell
cd i:\python\backtranslatess\frontend
npm run dev
```

- [ ] **Step 2: 验证 API 响应**

```powershell
curl -s http://localhost:8765/api/sessions | python -c "import json,sys; d=json.load(sys.stdin); print(f'Sessions: {len(d[\"sessions\"])}')"
curl -s http://localhost:8765/api/stats
```

Expected: Returns session count and stats.

- [ ] **Step 3: 打开浏览器验证前端**

Open `http://localhost:5173` in browser.
Expected: LearnPage loads, shows session selector and subtitle list.

---

## 自检清单

1. **Spec coverage**: 
   - FastAPI 后端 ✅ (3 个端点: sessions, subtitles, stats)
   - React 前端 ✅ (LearnPage 字幕列表)
   - CORS 配置 ✅
   - 不包含 AI/Tauri/认证 ✅ (符合范围)
2. **Placeholder scan**: ✅ 无 TBD/TODO
3. **Type consistency**: Pydantic v2 BaseModel ↔ TypeScript interfaces 字段名一致
