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
  promptTemplate: `You are a professional subtitle translator. Evaluate the user's translation directly and concisely.

{context}

Official: "{official}"

User: "{user_input}"

Return ONLY valid JSON:
{{
  "meaning_score": 0-100,
  "grammar_score": 0-100,
  "naturalness_score": 0-100,
  "subtitle_style_score": 0-100,
  "analysis": "Analysis in Chinese.",
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
