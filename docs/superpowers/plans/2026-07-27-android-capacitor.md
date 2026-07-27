# Android/Capacitor 纯前端移植 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** React 前端脱离 FastAPI 后端独立运行，用 Capacitor 打包 Android 应用

**Architecture:** sql.js 在浏览器中操作 SQLite，AI 调用直接 fetch，SRT 解析纯 TS

**Tech Stack:** sql.js / TypeScript / Capacitor / Vite

---

### Task 1: 数据库层 — sql.js 安装 + schema

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/db/index.ts`
- Create: `frontend/src/db/schema.ts`

- [ ] **Step 1: 安装 sql.js**

```powershell
cd i:\python\backtranslatess\frontend
npm install sql.js
npm install -D @types/sql.js
```

- [ ] **Step 2: 创建 DDL schema**

`frontend/src/db/schema.ts`:
```typescript
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
```

- [ ] **Step 3: 创建数据库初始化**

`frontend/src/db/index.ts`:
```typescript
import initSqlJs, { Database as SqlJsDatabase } from 'sql.js';
import { CREATE_TABLES_SQL } from './schema';

let db: SqlJsDatabase | null = null;

export async function initDatabase(): Promise<void> {
  const SQL = await initSqlJs({
    locateFile: (file: string) => `https://sql.js.org/dist/${file}`,
  });
  db = new SQL.Database();
  db.run(CREATE_TABLES_SQL);
}

export function getDb(): SqlJsDatabase {
  if (!db) throw new Error('Database not initialized. Call initDatabase() first.');
  return db;
}

export function saveDatabase(): Uint8Array {
  return getDb().export();
}

export function loadDatabase(data: Uint8Array): void {
  const SQL = initSqlJs({ locateFile: (file: string) => `https://sql.js.org/dist/${file}` });
  SQL.then(sql => {
    db = new sql.Database(data);
  });
}
```

---

### Task 2: 数据库操作层 — db/operations.ts

**Files:**
- Create: `frontend/src/db/operations.ts`

This file ports the 28 functions from `backtranslate/database/operations.py` to TypeScript.

```typescript
import { getDb } from './index';

// ===== TypeScript types matching Python models =====
export interface SessionRow {
  id: number; name: string; total_sentences: number;
  completed_sentences: number; created_at: string;
}

export interface SubtitleRow {
  id: number; session_id: number; idx: number;
  chinese: string; english_official: string;
  prev_chinese: string; prev_english: string;
  next_chinese: string; next_english: string;
}

export interface TranslationRow {
  id: number; subtitle_id: number; version: number;
  user_input: string; created_at: string;
}

export interface EvalRow {
  id: number; translation_id: number; status: string;
  meaning_score: number | null; grammar_score: number | null;
  naturalness_score: number | null; subtitle_style_score: number | null;
  analysis_text: string | null; suggested_expressions: string;
  error_message: string | null; created_at: string;
}

export interface ExpressionRow {
  id: number; phrase: string; source_subtitle_id: number | null;
  notes: string; collected_at: string;
}

// ===== Sessions =====

export function createSession(name: string, totalSentences: number): number {
  const db = getDb();
  db.run("INSERT INTO sessions (name, total_sentences) VALUES (?, ?)", [name, totalSentences]);
  return Number(db.exec("SELECT last_insert_rowid()")[0].values[0][0]);
}

export function getSession(sessionId: number): SessionRow | null {
  const db = getDb();
  const res = db.exec("SELECT * FROM sessions WHERE id = ?", [sessionId]);
  if (!res.length || !res[0].values.length) return null;
  return rowToObj<SessionRow>(res[0].columns, res[0].values[0]);
}

export function updateSessionCompleted(sessionId: number, count: number): void {
  getDb().run("UPDATE sessions SET completed_sentences = ? WHERE id = ?", [count, sessionId]);
}

export function clearSessionData(): void {
  getDb().run("DELETE FROM sessions");
}

export function getAllSessions(): SessionRow[] {
  const db = getDb();
  const res = db.exec("SELECT * FROM sessions ORDER BY id DESC");
  if (!res.length) return [];
  return res[0].values.map(v => rowToObj<SessionRow>(res[0].columns, v));
}

// ===== Subtitles =====

export function createSubtitlesBatch(sessionId: number, subtitles: Record<string, unknown>[]): void {
  const db = getDb();
  for (const sub of subtitles) {
    db.run(
      `INSERT INTO subtitles (session_id, idx, chinese, english_official, prev_chinese, prev_english, next_chinese, next_english)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [sessionId, sub.idx, sub.chinese, sub.english_official, sub.prev_chinese ?? '',
       sub.prev_english ?? '', sub.next_chinese ?? '', sub.next_english ?? '']
    );
  }
}

export function getSubtitlesForSession(sessionId: number): SubtitleRow[] {
  const db = getDb();
  const res = db.exec("SELECT * FROM subtitles WHERE session_id = ? ORDER BY idx", [sessionId]);
  if (!res.length) return [];
  return res[0].values.map(v => rowToObj<SubtitleRow>(res[0].columns, v));
}

// ===== Translations =====

export function createTranslation(subtitleId: number, userInput: string, version = 1): number {
  const db = getDb();
  db.run("INSERT INTO translations (subtitle_id, user_input, version) VALUES (?, ?, ?)",
    [subtitleId, userInput, version]);
  return Number(db.exec("SELECT last_insert_rowid()")[0].values[0][0]);
}

export function getAllTranslationsForSubtitle(subtitleId: number): TranslationRow[] {
  const db = getDb();
  const res = db.exec("SELECT * FROM translations WHERE subtitle_id = ? ORDER BY version", [subtitleId]);
  if (!res.length) return [];
  return res[0].values.map(v => rowToObj<TranslationRow>(res[0].columns, v));
}

// ===== Evaluations =====

export function createEvaluation(translationId: number, status = "pending"): number {
  const db = getDb();
  db.run("INSERT INTO evaluations (translation_id, status) VALUES (?, ?)", [translationId, status]);
  return Number(db.exec("SELECT last_insert_rowid()")[0].values[0][0]);
}

export function updateEvaluationStatus(
  evalId: number, status: string,
  meaning?: number | null, grammar?: number | null,
  naturalness?: number | null, subtitleStyle?: number | null,
  analysis?: string | null, suggested?: string | null,
  error?: string | null,
): void {
  getDb().run(
    `UPDATE evaluations SET status=?, meaning_score=?, grammar_score=?,
     naturalness_score=?, subtitle_style_score=?, analysis_text=?,
     suggested_expressions=?, error_message=? WHERE id=?`,
    [status, meaning ?? null, grammar ?? null, naturalness ?? null,
     subtitleStyle ?? null, analysis ?? null, suggested ?? null, error ?? null, evalId]
  );
}

export function getEvaluationForTranslation(translationId: number): EvalRow | null {
  const db = getDb();
  const res = db.exec("SELECT * FROM evaluations WHERE translation_id = ?", [translationId]);
  if (!res.length || !res[0].values.length) return null;
  return rowToObj<EvalRow>(res[0].columns, res[0].values[0]);
}

export function getEvaluationsForSession(sessionId: number): EvalRow[] {
  const db = getDb();
  const res = db.exec(
    `SELECT e.*, t.subtitle_id FROM evaluations e
     JOIN translations t ON e.translation_id = t.id
     JOIN subtitles s ON t.subtitle_id = s.id
     WHERE s.session_id = ? ORDER BY s.idx`, [sessionId]);
  if (!res.length) return [];
  return res[0].values.map(v => rowToObj<EvalRow>(res[0].columns, v));
}

// ===== Expressions =====

export function addExpression(phrase: string, sourceSubtitleId?: number | null, notes = ""): number {
  const db = getDb();
  db.run("INSERT INTO expressions (phrase, source_subtitle_id, notes) VALUES (?, ?, ?)",
    [phrase, sourceSubtitleId ?? null, notes]);
  return Number(db.exec("SELECT last_insert_rowid()")[0].values[0][0]);
}

export function getAllExpressions(): ExpressionRow[] {
  const db = getDb();
  const res = db.exec("SELECT * FROM expressions ORDER BY collected_at DESC");
  if (!res.length) return [];
  return res[0].values.map(v => rowToObj<ExpressionRow>(res[0].columns, v));
}

export function deleteExpression(expressionId: number): void {
  getDb().run("DELETE FROM expressions WHERE id = ?", [expressionId]);
}

// ===== Favorites =====

export function addFavorite(subtitleId: number): void {
  getDb().run("INSERT OR IGNORE INTO favorites (subtitle_id) VALUES (?)", [subtitleId]);
}

export function removeFavorite(subtitleId: number): void {
  getDb().run("DELETE FROM favorites WHERE subtitle_id = ?", [subtitleId]);
}

export function isFavorite(subtitleId: number): boolean {
  const res = getDb().exec("SELECT 1 FROM favorites WHERE subtitle_id = ?", [subtitleId]);
  return !!(res.length && res[0].values.length);
}

export function getFavorites(): Record<string, unknown>[] {
  const db = getDb();
  const res = db.exec(
    `SELECT f.id as fav_id, f.created_at as fav_created_at,
            s.id, s.session_id, s.idx, s.chinese, s.english_official,
            s.prev_chinese, s.prev_english, s.next_chinese, s.next_english
     FROM favorites f JOIN subtitles s ON f.subtitle_id = s.id
     ORDER BY f.created_at DESC`);
  if (!res.length) return [];
  return res[0].values.map(v => rowToObj(res[0].columns, v));
}

export function clearFavorites(): void {
  getDb().run("DELETE FROM favorites");
}

// ===== Self Ratings =====

export function upsertSelfRating(subtitleId: number, rating: number): void {
  getDb().run(
    "INSERT INTO self_ratings (subtitle_id, rating) VALUES (?, ?) ON CONFLICT(subtitle_id) DO UPDATE SET rating=?",
    [subtitleId, rating, rating]);
}

export function getSelfRating(subtitleId: number): number | null {
  const res = getDb().exec("SELECT rating FROM self_ratings WHERE subtitle_id = ?", [subtitleId]);
  return (res.length && res[0].values.length) ? Number(res[0].values[0][0]) : null;
}

// ===== Stats =====

export function recordSentenceCompleted(): void {
  const today = new Date().toISOString().slice(0, 10);
  getDb().run(
    `INSERT INTO streak_log (date, sentences_completed) VALUES (?, 1)
     ON CONFLICT(date) DO UPDATE SET sentences_completed = sentences_completed + 1`, [today]);
}

export function getTodayStats(): number {
  const today = new Date().toISOString().slice(0, 10);
  const res = getDb().exec("SELECT sentences_completed FROM streak_log WHERE date = ?", [today]);
  return (res.length && res[0].values.length) ? Number(res[0].values[0][0]) : 0;
}

export function getTotalSentences(): number {
  const res = getDb().exec("SELECT COALESCE(SUM(sentences_completed), 0) FROM streak_log");
  return Number(res[0].values[0][0]);
}

export function getStreakDays(): number {
  const db = getDb();
  const res = db.exec("SELECT date FROM streak_log WHERE sentences_completed > 0 ORDER BY date DESC");
  if (!res.length || !res[0].values.length) return 0;

  const rows = res[0].values.map(v => String(v[0]));
  let streak = 0;
  const today = new Date().toISOString().slice(0, 10);
  if (rows[0] !== today) {
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    if (rows[0] !== yesterday) return 0;
  }
  for (let i = 0; i < rows.length; i++) {
    const expected = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
    if (rows[i] === expected) streak++;
    else break;
  }
  return streak;
}

export function getAllStats(): { today: number; total: number; streak: number } {
  return { today: getTodayStats(), total: getTotalSentences(), streak: getStreakDays() };
}

// ===== Helper =====
function rowToObj<T>(columns: string[], values: unknown[]): T {
  const obj: Record<string, unknown> = {};
  columns.forEach((col, i) => { obj[col] = values[i]; });
  return obj as T;
}
```

- [ ] **Step 4: Verify sql.js works**

```typescript
// Create a quick test file or run inline:
import { initDatabase, getDb } from './db/index';
await initDatabase();
const db = getDb();
const res = db.exec("SELECT sqlite_version()");
console.log('sql.js works:', res[0].values[0][0]);
```

---

### Task 3: AI 客户端 + SRT 解析 (TypeScript)

**Files:**
- Create: `frontend/src/ai/client.ts`
- Create: `frontend/src/srt/parser.ts`
- Create: `frontend/src/srt/pairing.ts`
- Create: `frontend/src/config/index.ts`

- [ ] **Step 1: AI 客户端**

`frontend/src/ai/client.ts`:
```typescript
export interface AiResult {
  meaning_score: number;
  grammar_score: number;
  naturalness_score: number;
  subtitle_style_score: number;
  analysis: string;
  suggested_expressions: string[];
}

export interface AiConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
  promptTemplate: string;
  contextN: number;
}

export async function callAi(
  config: AiConfig,
  context: string,
  userInput: string,
  official: string,
): Promise<AiResult | null> {
  const prompt = config.promptTemplate
    .replace('{context}', context)
    .replace('{user_input}', userInput)
    .replace('{official}', official);

  try {
    const res = await fetch(`${config.baseUrl.replace(/\/+$/, '')}/chat/completions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${config.apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.model,
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.3,
      }),
      signal: AbortSignal.timeout(60000),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const content: string = data.choices?.[0]?.message?.content;
    if (!content) return null;
    return parseAiResponse(content);
  } catch { return null; }
}

function parseAiResponse(raw: string): AiResult | null {
  let content = raw.trim();
  const m = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (m) content = m[1].trim();
  try {
    const data = JSON.parse(content);
    return {
      meaning_score: Number(data.meaning_score ?? 0),
      grammar_score: Number(data.grammar_score ?? 0),
      naturalness_score: Number(data.naturalness_score ?? 0),
      subtitle_style_score: Number(data.subtitle_style_score ?? 0),
      analysis: String(data.analysis ?? ''),
      suggested_expressions: data.suggested_expressions ?? [],
    };
  } catch { return null; }
}

export function buildContext(
  subtitles: { idx: number; chinese: string }[],
  currentIdx: number,
  contextN: number,
): string {
  if (contextN === 0) return '';
  const parts: string[] = [];
  for (const s of subtitles) {
    if (s.idx < currentIdx && s.idx >= currentIdx - contextN) {
      parts.push(`前一句: ${s.chinese}`);
    } else if (s.idx > currentIdx && s.idx <= currentIdx + contextN) {
      parts.push(`后一句: ${s.chinese}`);
    }
  }
  return parts.length ? `上下文（仅供参考，不参与评分）:\n${parts.join('\n')}` : '';
}
```

- [ ] **Step 2: SRT 解析器**

`frontend/src/srt/parser.ts`:
```typescript
export interface SrtEntry {
  index: number;
  start: number;  // ms
  end: number;    // ms
  text: string;
}

function timestampToMs(ts: string): number {
  const [h, m, rest] = ts.split(':');
  const [s, ms] = rest.split(',');
  return Number(h) * 3600000 + Number(m) * 60000 + Number(s) * 1000 + Number(ms);
}

function stripTags(text: string): string {
  return text.replace(/<[^>]+>/g, '');
}

export function parseSrt(content: string): SrtEntry[] {
  const cleaned = content.replace(/^﻿/, '').replace(/\r\n/g, '\n');
  if (!cleaned.trim()) return [];

  const blocks = cleaned.trim().split(/\n\n+/).map(b => b.trim()).filter(Boolean);
  const result: SrtEntry[] = [];
  const pattern = /^(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n([\s\S]+)$/m;

  for (const block of blocks) {
    const m = block.match(pattern);
    if (!m) continue;
    result.push({
      index: Number(m[1]),
      start: timestampToMs(m[2]),
      end: timestampToMs(m[3]),
      text: stripTags(m[4].trim()),
    });
  }
  return result;
}
```

- [ ] **Step 3: SRT 配对**

`frontend/src/srt/pairing.ts`:
```typescript
import type { SrtEntry } from './parser';

export function pairByIndex(chinese: SrtEntry[], english: SrtEntry[]): [SrtEntry, SrtEntry][] {
  const n = Math.min(chinese.length, english.length);
  const pairs: [SrtEntry, SrtEntry][] = [];
  for (let i = 0; i < n; i++) {
    pairs.push([chinese[i], english[i]]);
  }
  return pairs;
}

export function pairByTimecode(chinese: SrtEntry[], english: SrtEntry[]): [SrtEntry, SrtEntry][] {
  const pairs: [SrtEntry, SrtEntry][] = [];
  let enIdx = 0;
  for (const ch of chinese) {
    while (enIdx < english.length && english[enIdx].end <= ch.start) {
      enIdx++;
    }
    if (enIdx < english.length && english[enIdx].start < ch.end) {
      pairs.push([ch, english[enIdx]]);
      enIdx++;
    }
  }
  return pairs;
}
```

- [ ] **Step 4: 配置存储**

`frontend/src/config/index.ts`:
```typescript
const CONFIG_KEY = 'backtranslate_config';

export interface AppConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
  contextN: number;
  fontSize: number;
  promptTemplate: string;
}

const DEFAULT_CONFIG: AppConfig = {
  baseUrl: 'https://api.deepseek.com',
  apiKey: '',
  model: 'deepseek-chat',
  contextN: 1,
  fontSize: 14,
  promptTemplate: `You are a professional subtitle translator. Evaluate the user's translation directly and concisely — no compliments, no encouragement, just the facts.

{context}

Official English subtitle: "{official}"

User's English translation: "{user_input}"

IMPORTANT: The context above is ONLY for understanding the surrounding dialogue. Do NOT evaluate the context. Only compare the user's translation against the official subtitle.

Rate on four dimensions (0-100):
- Meaning: Does the user's translation match the meaning of the official subtitle?
- Grammar: Is the English grammatically correct?
- Naturalness: Would a native speaker naturally say it this way?
- Subtitle Style: Is it concise and suitable for on-screen subtitles?

Return ONLY valid JSON:
{{
  "meaning_score": 0-100,
  "grammar_score": 0-100,
  "naturalness_score": 0-100,
  "subtitle_style_score": 0-100,
  "analysis": "Brief, direct analysis in Chinese.",
  "suggested_expressions": []
}}`,
};

export function loadConfig(): AppConfig {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { ...DEFAULT_CONFIG };
}

export function saveConfig(config: AppConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
}
```

- [ ] **Step 5: Verify TypeScript compilation**

```powershell
cd i:\python\backtranslatess\frontend
npx tsc --noEmit src/ai/client.ts src/srt/parser.ts src/srt/pairing.ts src/config/index.ts
```

Expected: No errors

---

### Task 4: 更新页面使用本地 DB

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/LearnPage.tsx`
- Modify: `frontend/src/pages/ReviewPage.tsx`
- Modify: `frontend/src/pages/FavoritesPage.tsx`
- Modify: `frontend/src/pages/ExpressionsPage.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`

This is the largest task. Each page needs to be updated to:
1. Import from `../db/operations` instead of `../api/client`
2. Call local database functions directly
3. For AI calls, call `callAi()` from `../ai/client` directly in LearnPage

Rather than rewriting every page completely, the approach is:
- Keep the existing API layer as an alternative (can still be used in dev mode)
- Create a `useLocalMode` flag/hook that determines whether to use local DB or API
- Initially default to local DB mode

Actually, the cleanest approach: update each page's imports and data access layer. For the LearnPage, replace API calls with direct DB calls. For AI, call the local AI client directly.

Let me dispatch this as an agent with complete code for each page change.

Since this task is very large, I'll split it into sub-tasks:
- Task 4a: App.tsx - add initDatabase, switch to local mode
- Task 4b: LearnPage - use local DB + AI
- Task 4c: ReviewPage - use local DB
- Task 4d: FavoritesPage + ExpressionsPage - use local DB
- Task 4e: SettingsPage - use local config

Let me dispatch this through the subagent-driven process.

---

### Task 5: Capacitor Android 打包

**Files:**
- Create: `frontend/capacitor.config.ts`
- Run: `npx cap add android`

- [ ] **Step 1: Install Capacitor**

```powershell
cd i:\python\backtranslatess\frontend
npm install @capacitor/core @capacitor/cli @capacitor/android
```

- [ ] **Step 2: Init Capacitor**

```powershell
npx cap init backtranslate com.backtranslate.app --web-dir dist
```

- [ ] **Step 3: Add Android platform**

```powershell
npx cap add android
```

- [ ] **Step 4: Build and copy**

```powershell
npm run build
npx cap copy
npx cap sync
```

- [ ] **Step 5: Open in Android Studio**

```powershell
npx cap open android
```
