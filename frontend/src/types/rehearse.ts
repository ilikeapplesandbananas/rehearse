export interface ProjectHighlight {
  name: string;
  summary: string;
  technologies: string[];
  scale_or_impact: string;
}

export interface CandidateProfile {
  candidate_name: string;
  experience_level: string;
  years_experience: string;
  location?: string;
  primary_skills: string[];
  projects: ProjectHighlight[];
  work_experience?: string[];
  certifications?: string[];
  education: string;
  extraction_method?: string;
  projects_summary_line: string;
  detected_target_company?: string;
  detected_target_role?: string;
  seniority_track?: string;
}

export interface CVPresetMeta {
  id: string;
  label: string;
  filename: string;
  default_company: string;
  default_role: string;
  default_jd: string;
}

export interface CVDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  page_count: number;
  raw_text: string;
  candidate_profile: CandidateProfile;
  created_at: string;
}

export interface InterviewRoundInfo {
  stage: string;
  name: string;
  duration: string;
  format: string;
}

export interface CompanyResearchResult {
  company_name: string;
  normalized_key: string;
  archetype_id: string;
  archetype_name: string;
  archetype_short_label: string;
  shared_companies: string[];
  deduplication_note: string;
  summary: string;
  rounds: InterviewRoundInfo[];
  company_nuances: string[];
  evaluation_bar: string[];
  role_key: string;
  role_label: string;
  role_core_topics: string[];
  seniority_track?: string;
  researched_job_description?: string;
  explore_pillars?: ExplorePillar[];
  company_grading_rubric?: string[];
  expected_answer_structure?: string;
  coding_and_leetcode_patterns?: string[];
  role_grading_focus?: string[];
  researched_live: boolean;
  sources: string[];
}

export interface ArchetypeOverview {
  id: string;
  name: string;
  short_label: string;
  summary: string;
  shared_companies: string[];
  standard_rounds: InterviewRoundInfo[];
  evaluation_bar: string[];
}

export interface KnownCompanyItem {
  name: string;
  archetype_id: string;
  archetype_label: string;
}

export interface ExplorePillar {
  index: string;
  title: string;
  description: string;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  confidence: number;
  is_filler: boolean;
}

export interface AwkwardPause {
  start_sec: number;
  end_sec: number;
  duration_sec: number;
  before_word: string;
  after_word: string;
}

export interface DeliveryMetrics {
  duration_seconds: number;
  duration_formatted: string;
  word_count: number;
  speaking_pace_wpm: number;
  pace_label: string;
  pace_status: "good" | "warn" | "neutral";
  filler_count: number;
  filler_per_min: number;
  filler_label: string;
  filler_status: "good" | "warn" | "neutral";
  filler_breakdown: Record<string, number>;
  longest_pause_sec: number;
  pause_label: string;
  pause_status: "good" | "warn" | "neutral";
  awkward_pauses: AwkwardPause[];
  hedging_phrases: string[];
  annotated_transcript: string;
  stt_provider: string;
  has_word_timestamps: boolean;
}

export interface RubricScores {
  communication: number;
  communication_note: string;
  technical_depth: number;
  technical_depth_note: string;
  structure: number;
  structure_note: string;
  confidence: number;
  confidence_note: string;
  overall: number;
}

export interface FeedbackGap {
  index: string;
  title: string;
  detail: string;
}

export interface StudyMaterialItem {
  topic: string;
  subtitle: string;
  why: string;
  search_query_or_resource: string;
  resource_url: string;
}

export interface EvaluationResult {
  headline: string;
  scores: RubricScores;
  gaps: FeedbackGap[];
  what_went_wrong: string;
  what_was_missing: string;
  how_to_fix: string;
  fix_formula: string;
  sample_strong_answer: string;
  sample_paragraphs: string[];
  hedging_phrases_found: string[];
  study_material: StudyMaterialItem[];
  llm_provider: string;
  llm_model: string;
}

export interface QuestionAttempt {
  id: string;
  attempt_number: number;
  duration_seconds: number;
  stt_provider: string;
  transcript_verbatim: string;
  transcript_clean: string;
  word_timestamps: WordTimestamp[];
  delivery_metrics: DeliveryMetrics;
  evaluation: EvaluationResult;
  created_at: string;
}

export interface SessionQuestion {
  id: string;
  order_index: number;
  short_title: string;
  category: string;
  question_text: string;
  source_attribution: string;
  guidance_cues: string[];
  evaluation_focus: string[];
  status: "up_next" | "in_progress" | "completed";
  latest_attempt: QuestionAttempt | null;
}

export interface InterviewSession {
  id: string;
  cv_document_id: string | null;
  company_name: string;
  target_role: string;
  round_focus: string;
  job_description: string;
  jd_signals: string[];
  company_research: CompanyResearchResult;
  candidate_profile: CandidateProfile;
  explore_pillars: ExplorePillar[];
  status: "setup" | "in_progress" | "completed";
  current_question_index: number;
  overall_score: number | null;
  questions: SessionQuestion[];
  created_at: string;
  updated_at: string;
}

export interface StudyPlanRecord {
  id: string;
  session_id: string | null;
  company_name: string;
  target_role: string;
  topic: string;
  subtitle: string;
  why: string;
  search_query_or_resource: string;
  resource_url: string;
  completed: boolean;
  created_at: string;
}

export interface OverviewStats {
  sessions_this_week: number;
  weekly_goal: number;
  total_sessions: number;
  total_answers_evaluated: number;
  average_overall: number | null;
  average_scores: {
    communication: number;
    technical_depth: number;
    structure: number;
    confidence: number;
  };
  recent_sessions: {
    id: string;
    company_name: string;
    target_role: string;
    status: string;
    overall_score: number | null;
    completed_questions: number;
    total_questions: number;
    created_at: string;
    updated_at: string;
  }[];
  active_llm: { provider: string; model: string };
  active_stt: { provider: string; model: string };
  active_tts: { provider: string; model: string };
}

export interface EngineSettingsStatus {
  llm: { provider: string; model: string; frontier_enabled: boolean };
  stt: { provider: string; model: string; cloud_verbatim_enabled: boolean };
  tts: { provider: string; model: string };
  keys_configured: Record<string, boolean>;
  models: Record<string, string>;
}

export type NavTab = "overview" | "practice" | "sessions" | "study";
export type PracticeStage = "setup" | "voice" | "review";
