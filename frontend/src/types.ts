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
  status: string;
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
  source_subtitle_id?: number;
}

export interface ExpressionListResponse {
  expressions: ExpressionItem[];
}
