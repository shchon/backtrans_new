import type {
  SessionListResponse, SubtitleListResponse, Stats,
  TranslateRequest, TranslateResponse, EvaluationStatus,
  SrtImportRequest, SrtImportResponse, EvaluationListResponse,
  ConfigData, ExpressionItem, ExpressionListResponse,
} from '../types';

const API_BASE = 'http://localhost:8765/api';

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: {'Content-Type': 'application/json', ...init?.headers},
    ...init,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// Sessions
export async function listSessions(): Promise<SessionListResponse> {
  return fetchJson<SessionListResponse>(`${API_BASE}/sessions`);
}

export async function getSessionSubtitles(sessionId: number): Promise<SubtitleListResponse> {
  return fetchJson<SubtitleListResponse>(`${API_BASE}/sessions/${sessionId}/subtitles`);
}

export async function importSrt(req: SrtImportRequest): Promise<SrtImportResponse> {
  return fetchJson<SrtImportResponse>(`${API_BASE}/sessions/import`, {
    method: 'POST', body: JSON.stringify(req),
  });
}

export async function completeSession(sessionId: number): Promise<void> {
  await fetch(`${API_BASE}/sessions/${sessionId}/complete`, {method: 'POST'});
}

// Translation + Evaluation
export async function submitTranslation(sessionId: number, req: TranslateRequest): Promise<TranslateResponse> {
  return fetchJson<TranslateResponse>(`${API_BASE}/sessions/${sessionId}/translate`, {
    method: 'POST', body: JSON.stringify(req),
  });
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

// Config
export async function getConfig(): Promise<ConfigData> {
  return fetchJson<ConfigData>(`${API_BASE}/config`);
}

export async function updateConfig(cfg: Partial<ConfigData>): Promise<ConfigData> {
  return fetchJson<ConfigData>(`${API_BASE}/config`, {
    method: 'PUT', body: JSON.stringify(cfg),
  });
}

// Expressions
export async function getExpressions(): Promise<ExpressionListResponse> {
  return fetchJson<ExpressionListResponse>(`${API_BASE}/expressions`);
}

export async function addExpressionApi(phrase: string, subtitleId?: number): Promise<ExpressionItem> {
  return fetchJson<ExpressionItem>(`${API_BASE}/expressions`, {
    method: 'POST', body: JSON.stringify({phrase, subtitle_id: subtitleId ?? 0}),
  });
}

export async function deleteExpressionApi(exprId: number): Promise<void> {
  await fetch(`${API_BASE}/expressions/${exprId}`, {method: 'DELETE'});
}

// Favorites
export async function getFavoritesApi(): Promise<Record<string, unknown>[]> {
  return fetchJson(`${API_BASE}/favorites`);
}

export async function addFavoriteApi(subtitleId: number): Promise<void> {
  await fetch(`${API_BASE}/favorites/${subtitleId}`, {method: 'POST'});
}

export async function removeFavoriteApi(subtitleId: number): Promise<void> {
  await fetch(`${API_BASE}/favorites/${subtitleId}`, {method: 'DELETE'});
}

// Stats
export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>(`${API_BASE}/stats`);
}
