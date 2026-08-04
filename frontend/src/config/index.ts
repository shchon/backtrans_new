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

Return ONLY the following JSON format, nothing else:
{
  "meaning_score": 85,
  "grammar_score": 85,
  "naturalness_score": 85,
  "subtitle_style_score": 85,
  "analysis": "Detailed analysis in Chinese here...",
  "suggested_expressions": ["expression1", "expression2"]
}`,
};

export function loadConfig(): AppConfig {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) {
      const data = JSON.parse(raw) as Partial<AppConfig>;
      // Migrate old Python-style {{ }} prompt to single braces
      if (data.promptTemplate) {
        data.promptTemplate = data.promptTemplate.replace(/\{\{/g, '{').replace(/\}\}/g, '}');
      }
      return { ...DEFAULT_CONFIG, ...data };
    }
  } catch { /* ignore */ }
  return { ...DEFAULT_CONFIG };
}

export function saveConfig(config: AppConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
}
