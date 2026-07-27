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

export async function testConnection(
  baseUrl: string, apiKey: string, model: string,
): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl.replace(/\/+$/, '')}/chat/completions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: 'Say OK and nothing else.' }],
        max_tokens: 10,
      }),
      signal: AbortSignal.timeout(15000),
    });
    return res.ok;
  } catch { return false; }
}
