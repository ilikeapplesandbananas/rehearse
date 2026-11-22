from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ProjectHighlight(BaseModel):
    name: str
    summary: str
    technologies: list[str] = Field(default_factory=list)
    scale_or_impact: str = ""


class CandidateProfile(BaseModel):
    candidate_name: str = "Mbesa Lephoto"
    experience_level: str = "Final-year BSc IT (SWE)"
    years_experience: str = "82.4% avg · 14 distinctions"
    location: str = "Midrand, Gauteng"
    primary_skills: list[str] = Field(default_factory=list)
    projects: list[ProjectHighlight] = Field(default_factory=list)
    work_experience: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    education: str = ""
    extraction_method: str = "Text extracted"
    projects_summary_line: str = ""
    detected_target_company: str = ""
    detected_target_role: str = ""
    seniority_track: str = "intern_grad"


class CVDocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int
    raw_text: str
    candidate_profile: CandidateProfile
    created_at: str


class InterviewRoundInfo(BaseModel):
    stage: str
    name: str
    duration: str
    format: str


class ExplorePillar(BaseModel):
    index: str
    title: str
    description: str


class CompanyResearchResult(BaseModel):
    company_name: str
    normalized_key: str
    archetype_id: str
    archetype_name: str
    archetype_short_label: str
    shared_companies: list[str] = Field(default_factory=list)
    deduplication_note: str = ""
    summary: str
    rounds: list[InterviewRoundInfo] = Field(default_factory=list)
    company_nuances: list[str] = Field(default_factory=list)
    evaluation_bar: list[str] = Field(default_factory=list)
    role_key: str = "backend"
    role_label: str = "Backend Engineer"
    role_core_topics: list[str] = Field(default_factory=list)
    seniority_track: str = "intern_grad"
    researched_job_description: str = ""
    explore_pillars: list[ExplorePillar] = Field(default_factory=list)
    company_grading_rubric: list[str] = Field(default_factory=list)
    expected_answer_structure: str = ""
    coding_and_leetcode_patterns: list[str] = Field(default_factory=list)
    role_grading_focus: list[str] = Field(default_factory=list)
    researched_live: bool = False
    sources: list[str] = Field(default_factory=list)


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    confidence: float = 0.99
    is_filler: bool = False


class AwkwardPause(BaseModel):
    start_sec: float
    end_sec: float
    duration_sec: float
    before_word: str = ""
    after_word: str = ""


class DeliveryMetrics(BaseModel):
    duration_seconds: float
    duration_formatted: str
    word_count: int
    speaking_pace_wpm: int
    pace_label: str  # Steady | Too fast | Brisk | Measured | Slow
    pace_status: Literal["good", "warn", "neutral"] = "good"
    filler_count: int
    filler_per_min: float
    filler_label: str  # Low | Moderate | Reduce
    filler_status: Literal["good", "warn", "neutral"] = "good"
    filler_breakdown: dict[str, int] = Field(default_factory=dict)
    longest_pause_sec: float
    pause_label: str  # Smooth | Brief | Noticeable
    pause_status: Literal["good", "warn", "neutral"] = "good"
    awkward_pauses: list[AwkwardPause] = Field(default_factory=list)
    hedging_phrases: list[str] = Field(default_factory=list)
    annotated_transcript: str = ""
    stt_provider: str = "browser_live"
    has_word_timestamps: bool = False


class RubricScores(BaseModel):
    communication: int = Field(ge=0, le=100)
    communication_note: str = "Clear and well-paced"
    technical_depth: int = Field(ge=0, le=100)
    technical_depth_note: str = "Solid fundamentals"
    structure: int = Field(ge=0, le=100)
    structure_note: str = "A logical progression"
    confidence: int = Field(ge=0, le=100)
    confidence_note: str = "Steady vocal delivery"
    overall: int = Field(ge=0, le=100)


class FeedbackGap(BaseModel):
    index: str
    title: str
    detail: str


class StudyMaterialItem(BaseModel):
    topic: str
    subtitle: str = ""
    why: str
    search_query_or_resource: str
    resource_url: str = ""


class EvaluationResult(BaseModel):
    headline: str = "Good experience. Let’s make it land."
    scores: RubricScores
    gaps: list[FeedbackGap] = Field(default_factory=list)
    what_went_wrong: str
    what_was_missing: str
    how_to_fix: str
    fix_formula: str = ""
    sample_strong_answer: str
    sample_paragraphs: list[str] = Field(default_factory=list)
    hedging_phrases_found: list[str] = Field(default_factory=list)
    study_material: list[StudyMaterialItem] = Field(default_factory=list)
    llm_provider: str = "local_coach"
    llm_model: str = ""


class QuestionAttemptResponse(BaseModel):
    id: str
    attempt_number: int
    duration_seconds: float
    stt_provider: str
    transcript_verbatim: str
    transcript_clean: str
    word_timestamps: list[WordTimestamp] = Field(default_factory=list)
    delivery_metrics: DeliveryMetrics
    evaluation: EvaluationResult
    created_at: str


class SessionQuestionResponse(BaseModel):
    id: str
    order_index: int
    short_title: str
    category: str
    question_text: str
    source_attribution: str
    guidance_cues: list[str] = Field(default_factory=list)
    evaluation_focus: list[str] = Field(default_factory=list)
    status: Literal["up_next", "in_progress", "completed"] = "up_next"
    latest_attempt: QuestionAttemptResponse | None = None


class InterviewSessionResponse(BaseModel):
    id: str
    cv_document_id: str | None = None
    company_name: str
    target_role: str
    round_focus: str = "full_loop"
    job_description: str
    jd_signals: list[str] = Field(default_factory=list)
    company_research: CompanyResearchResult
    candidate_profile: CandidateProfile
    explore_pillars: list[ExplorePillar] = Field(default_factory=list)
    status: Literal["setup", "in_progress", "completed"] = "in_progress"
    current_question_index: int = 0
    overall_score: int | None = None
    questions: list[SessionQuestionResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class CreateSessionRequest(BaseModel):
    cv_document_id: str | None = None
    cv_raw_text: str | None = None
    candidate_profile: CandidateProfile | None = None
    company_name: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    job_description: str = Field(min_length=10)
    round_focus: str = "full_loop"
    question_count: int = Field(default=6, ge=5, le=8)


class StudyPlanRecord(BaseModel):
    id: str
    session_id: str | None = None
    company_name: str = ""
    target_role: str = ""
    topic: str
    subtitle: str = ""
    why: str
    search_query_or_resource: str
    resource_url: str
    completed: bool = False
    created_at: str


class RuntimeSettingsUpdate(BaseModel):
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None
    LLM_PROVIDER: str | None = None
    DEEPGRAM_API_KEY: str | None = None
    DEEPGRAM_MODEL: str | None = None
    GROQ_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None


class OverviewStatsResponse(BaseModel):
    sessions_this_week: int
    weekly_goal: int
    total_sessions: int
    total_answers_evaluated: int
    average_overall: int | None
    average_scores: dict[str, int]
    recent_sessions: list[dict[str, Any]]
    active_llm: dict[str, str]
    active_stt: dict[str, str]
    active_tts: dict[str, str]
