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

function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

export type CallAiResult =
  | { ok: true; result: AiResult }
  | { ok: false; error: string };

export async function callAi(
  config: AiConfig,
  context: string,
  userInput: string,
  official: string,
): Promise<CallAiResult> {
  const prompt = config.promptTemplate
    .replace('{context}', context)
    .replace('{user_input}', userInput)
    .replace('{official}', official);

  try {
    const res = await fetchWithTimeout(
      `${config.baseUrl.replace(/\/+$/, '')}/chat/completions`,
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${config.apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: config.model,
          messages: [{ role: 'user', content: prompt }],
          temperature: 0.3,
        }),
      },
      120000,
    );
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      return { ok: false, error: `HTTP ${res.status}: ${text.slice(0, 200)}` };
    }
    const data = await res.json();
    const content: string = data.choices?.[0]?.message?.content;
    if (!content) return { ok: false, error: 'AI 返回了空内容' };
    const parsed = parseAiResponse(content);
    if (!parsed) return { ok: false, error: `AI 返回内容无法解析为 JSON。原始返回: ${content.slice(0, 500)}` };
    return { ok: true, result: parsed };
  } catch (e) {
    return { ok: false, error: String(e).slice(0, 300) };
  }
}

function parseAiResponse(raw: string): AiResult | null {
  let content = raw.trim();

  // Strip markdown code fences (with or without language tag)
  const fenceMatch = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (fenceMatch) content = fenceMatch[1].trim();

  // Try to find JSON object boundaries if there's extra text
  const objMatch = content.match(/\{[\s\S]*\}/);
  if (objMatch) content = objMatch[0];

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
  } catch {
    // Try again with single quotes converted to double quotes
    try {
      const fixed = content.replace(/'/g, '"');
      const data = JSON.parse(fixed);
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

export async function testConnection(
  baseUrl: string, apiKey: string, model: string,
): Promise<{ ok: boolean; error?: string }> {
  try {
    const url = `${baseUrl.replace(/\/+$/, '')}/chat/completions`;
    const res = await fetchWithTimeout(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: 'Say OK and nothing else.' }],
        max_tokens: 10,
      }),
    }, 30000);
    if (res.ok) return { ok: true };
    const text = await res.text().catch(() => '');
    return { ok: false, error: `HTTP ${res.status}: ${text.slice(0, 200)}` };
  } catch (e) {
    return { ok: false, error: String(e).slice(0, 200) };
  }
}
