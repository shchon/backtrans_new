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
  // First get all favorite subtitle_ids
  const favRes = db.exec("SELECT subtitle_id, created_at FROM favorites ORDER BY created_at DESC");
  if (!favRes.length) return [];

  const results: Record<string, unknown>[] = [];
  for (const row of favRes[0].values) {
    const subtitleId = Number(row[0]);
    const createdAt = String(row[1] ?? '');
    // Then get subtitle data
    const subRes = db.exec("SELECT id, session_id, idx, chinese, english_official, prev_chinese, prev_english, next_chinese, next_english FROM subtitles WHERE id = ?", [subtitleId]);
    if (subRes.length && subRes[0].values.length) {
      const sub = rowToObj<Record<string, unknown>>(subRes[0].columns, subRes[0].values[0]);
      sub.fav_created_at = createdAt;
      results.push(sub);
    }
  }
  return results;
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
