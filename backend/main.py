from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from data.cv_presets import CV_PRESETS
from models.schemas import (
    CVDocumentResponse,
    CandidateProfile,
    CompanyResearchResult,
    CreateSessionRequest,
    InterviewSessionResponse,
    OverviewStatsResponse,
    QuestionAttemptResponse,
    RuntimeSettingsUpdate,
    StudyPlanRecord,
    WordTimestamp,
)
from services.company_research import (
    list_all_archetypes,
    list_known_companies,
    research_company_and_role,
)
from services.cv_parser import (
    SAMPLE_CV_TEXT,
    extract_jd_signals,
    extract_profile_heuristic,
    extract_profile_with_computer_vision,
    extract_text_and_images_from_upload,
)
from services.database import (
    create_session_record,
    delete_cv_document,
    delete_session_record,
    get_cv_document,
    get_overview_stats,
    get_session_record,
    init_db,
    list_session_records,
    list_study_items,
    save_cv_document,
    save_question_attempt,
    toggle_study_item,
)
from services.delivery_metrics import analyze_delivery_signals
from services.llm_engine import (
    enrich_candidate_profile_with_llm,
    evaluate_interview_answer,
    generate_tailored_interview,
)
from services.transcriber import synthesize_speech_bytes, transcribe_audio_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rehearse")

app = FastAPI(
    title="Rehearse API",
    description="AI Mock Interview Coach: Company Research, Verbatim STT, Delivery Telemetry & Rubric Grading",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    llm_p, llm_m = settings.active_llm_info()
    stt_p, stt_m = settings.active_stt_info()
    logger.info("Rehearse API ready | LLM=%s:%s | STT=%s:%s", llm_p, llm_m, stt_p, stt_m)


@app.get("/api/health")
def health() -> dict[str, Any]:
    llm_p, llm_m = settings.active_llm_info()
    stt_p, stt_m = settings.active_stt_info()
    tts_p, tts_m = settings.active_tts_info()
    return {
        "status": "ok",
        "app": "rehearse",
        "llm": {"provider": llm_p, "model": llm_m, "frontier_enabled": llm_p != "local_coach"},
        "stt": {"provider": stt_p, "model": stt_m, "cloud_verbatim_enabled": stt_p != "browser_live"},
        "tts": {"provider": tts_p, "model": tts_m},
    }


@app.get("/api/settings/status")
def get_settings_status() -> dict[str, Any]:
    llm_p, llm_m = settings.active_llm_info()
    stt_p, stt_m = settings.active_stt_info()
    tts_p, tts_m = settings.active_tts_info()
    return {
        "llm": {"provider": llm_p, "model": llm_m, "frontier_enabled": llm_p != "local_coach"},
        "stt": {"provider": stt_p, "model": stt_m, "cloud_verbatim_enabled": stt_p != "browser_live"},
        "tts": {"provider": tts_p, "model": tts_m},
        "keys_configured": {
            "GEMINI_API_KEY": bool(settings.gemini_api_key),
            "ANTHROPIC_API_KEY": bool(settings.anthropic_api_key),
            "OPENAI_API_KEY": bool(settings.openai_api_key),
            "DEEPGRAM_API_KEY": bool(settings.deepgram_api_key),
            "GROQ_API_KEY": bool(settings.groq_api_key),
            "ELEVENLABS_API_KEY": bool(settings.elevenlabs_api_key),
            "TAVILY_API_KEY": bool(settings.tavily_api_key),
        },
        "models": {
            "GEMINI_MODEL": settings.gemini_model,
            "ANTHROPIC_MODEL": settings.anthropic_model,
            "OPENAI_MODEL": settings.openai_model,
            "DEEPGRAM_MODEL": settings.deepgram_model,
            "LLM_PROVIDER": settings.llm_provider,
        },
    }


@app.post("/api/settings/keys")
def update_settings_keys(payload: RuntimeSettingsUpdate) -> dict[str, Any]:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None and v != ""}
    settings.update_runtime_keys(updates)
    return get_settings_status()


# ---------------------------------------------------------------------------
# Stage 1: Context Ingestion (CV PDF/DOCX + Company & Role Research)
# ---------------------------------------------------------------------------
@app.post("/api/cv/upload", response_model=CVDocumentResponse)
async def upload_cv(file: UploadFile = File(...)) -> CVDocumentResponse:
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CV file exceeds the 10 MB limit.")

    filename = file.filename or "Resume.pdf"
    raw_text, file_type, page_count, page_images = extract_text_and_images_from_upload(filename, content)
    if len(raw_text.strip()) < 20 and not page_images:
        raise HTTPException(
            status_code=422,
            detail="Could not extract readable text or page images from this file. Please upload a PDF, DOCX, or PNG/JPG CV.",
        )

    heuristic = extract_profile_heuristic(raw_text)
    profile = await extract_profile_with_computer_vision(raw_text, page_images, heuristic)
    saved = save_cv_document(
        filename=filename,
        file_type=file_type,
        file_size_bytes=len(content),
        page_count=page_count,
        raw_text=raw_text,
        candidate_profile=profile.model_dump(),
    )
    return CVDocumentResponse(**saved)


@app.get("/api/cv/presets")
def list_cv_presets() -> dict[str, Any]:
    return {
        "presets": [
            {
                "id": p["id"],
                "label": p["label"],
                "filename": p["filename"],
                "default_company": p["default_company"],
                "default_role": p["default_role"],
                "default_jd": p["default_jd"],
            }
            for p in CV_PRESETS.values()
        ]
    }


@app.post("/api/cv/preset/{preset_id}", response_model=CVDocumentResponse)
async def load_cv_preset(preset_id: str) -> CVDocumentResponse:
    preset = CV_PRESETS.get(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"CV preset '{preset_id}' not found.")
    raw_text = preset["raw_text"]
    heuristic = extract_profile_heuristic(raw_text)
    heuristic.extraction_method = "Text extracted"
    saved = save_cv_document(
        filename=preset["filename"],
        file_type="PDF",
        file_size_bytes=len(raw_text.encode("utf-8")) * 24,
        page_count=3 if len(raw_text) > 3600 else 2,
        raw_text=raw_text,
        candidate_profile=heuristic.model_dump(),
    )
    return CVDocumentResponse(**saved)


@app.post("/api/cv/sample", response_model=CVDocumentResponse)
async def load_sample_cv() -> CVDocumentResponse:
    return await load_cv_preset("stripe_data_analyst")


@app.delete("/api/cv/{doc_id}")
def remove_cv(doc_id: str) -> dict[str, bool]:
    return {"deleted": delete_cv_document(doc_id)}


@app.get("/api/research/archetypes")
def get_archetypes() -> dict[str, Any]:
    return {
        "archetypes": list_all_archetypes(),
        "companies": list_known_companies(),
    }


class CompanyResearchRequest(BaseModel):
    company_name: str
    target_role: str = "Backend Engineer"
    job_description: str = ""
    experience_level: str = ""
    force_live: bool = False


@app.post("/api/research/company", response_model=CompanyResearchResult)
async def research_company(req: CompanyResearchRequest) -> CompanyResearchResult:
    return await research_company_and_role(
        company_name=req.company_name,
        target_role=req.target_role,
        job_description=req.job_description,
        force_live=req.force_live,
        experience_level=req.experience_level,
    )


# ---------------------------------------------------------------------------
# Stage 2: Tailored Interview Session Generation
# ---------------------------------------------------------------------------
@app.post("/api/sessions", response_model=InterviewSessionResponse)
async def create_interview_session(req: CreateSessionRequest) -> InterviewSessionResponse:
    cv_raw_text = req.cv_raw_text or ""
    candidate_profile = req.candidate_profile

    if req.cv_document_id:
        doc = get_cv_document(req.cv_document_id)
        if doc:
            cv_raw_text = doc["raw_text"]
            candidate_profile = CandidateProfile(**doc["candidate_profile"])

    if not candidate_profile:
        cv_raw_text = cv_raw_text or SAMPLE_CV_TEXT
        candidate_profile = extract_profile_heuristic(cv_raw_text)

    company_research = await research_company_and_role(
        company_name=req.company_name,
        target_role=req.target_role,
        job_description=req.job_description,
        experience_level=candidate_profile.experience_level,
    )
    jd_signals = extract_jd_signals(req.job_description, req.target_role)

    pillars, questions = await generate_tailored_interview(
        candidate_profile=candidate_profile,
        cv_raw_text=cv_raw_text,
        company_research=company_research,
        job_description=req.job_description,
        round_focus=req.round_focus,
        question_count=req.question_count,
    )

    session = create_session_record(
        cv_document_id=req.cv_document_id,
        company_name=company_research.company_name,
        target_role=req.target_role.strip(),
        round_focus=req.round_focus,
        job_description=req.job_description.strip(),
        jd_signals=jd_signals,
        company_research=company_research.model_dump(),
        candidate_profile=candidate_profile.model_dump(),
        explore_pillars=[p.model_dump() for p in pillars],
        questions=questions,
    )
    return InterviewSessionResponse(**session)


@app.get("/api/sessions", response_model=list[InterviewSessionResponse])
def list_sessions() -> list[InterviewSessionResponse]:
    return [InterviewSessionResponse(**s) for s in list_session_records()]


@app.get("/api/sessions/{session_id}", response_model=InterviewSessionResponse)
def get_session(session_id: str) -> InterviewSessionResponse:
    s = get_session_record(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return InterviewSessionResponse(**s)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, bool]:
    return {"deleted": delete_session_record(session_id)}


# ---------------------------------------------------------------------------
# Stage 3 & 4: Pristine Voice Transcription, Delivery Telemetry & LLM Grading
# ---------------------------------------------------------------------------
@app.post("/api/transcribe")
async def transcribe_only(
    audio: UploadFile | None = File(default=None),
    fallback_transcript: str = Form(default=""),
    duration_seconds: float = Form(default=0.0),
) -> dict[str, Any]:
    audio_bytes = await audio.read() if audio else b""
    stt = await transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        content_type=(audio.content_type if audio else "audio/webm") or "audio/webm",
        filename=(audio.filename if audio else "answer.webm") or "answer.webm",
        fallback_transcript=fallback_transcript,
        duration_seconds=duration_seconds,
    )
    eff_duration = stt["duration_seconds"] if stt["duration_seconds"] > 0.5 else duration_seconds
    metrics = analyze_delivery_signals(
        transcript_verbatim=stt["transcript_verbatim"],
        duration_seconds=eff_duration,
        word_timestamps=stt["word_timestamps"],
        stt_provider=stt["stt_provider"],
    )
    return {
        "stt_provider": stt["stt_provider"],
        "transcript_verbatim": stt["transcript_verbatim"],
        "transcript_clean": stt["transcript_clean"],
        "word_timestamps": [w.model_dump() for w in stt["word_timestamps"]],
        "delivery_metrics": metrics.model_dump(),
    }


@app.post(
    "/api/sessions/{session_id}/questions/{question_id}/evaluate",
    response_model=QuestionAttemptResponse,
)
async def submit_and_evaluate_answer(
    session_id: str,
    question_id: str,
    audio: UploadFile | None = File(default=None),
    fallback_transcript: str = Form(default=""),
    duration_seconds: float = Form(default=0.0),
) -> QuestionAttemptResponse:
    session = get_session_record(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    question = next((q for q in session["questions"] if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found in session.")

    audio_bytes = await audio.read() if audio else b""
    stt = await transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        content_type=(audio.content_type if audio else "audio/webm") or "audio/webm",
        filename=(audio.filename if audio else "answer.webm") or "answer.webm",
        fallback_transcript=fallback_transcript,
        duration_seconds=duration_seconds,
    )

    verbatim = stt["transcript_verbatim"].strip()
    if not verbatim:
        raise HTTPException(
            status_code=422,
            detail="No spoken words were detected. Check your microphone or speak a bit longer before finishing.",
        )

    eff_duration = stt["duration_seconds"] if stt["duration_seconds"] > 0.5 else duration_seconds
    timestamps: list[WordTimestamp] = stt["word_timestamps"]
    delivery_metrics = analyze_delivery_signals(
        transcript_verbatim=verbatim,
        duration_seconds=eff_duration,
        word_timestamps=timestamps,
        stt_provider=stt["stt_provider"],
    )

    candidate_profile = CandidateProfile(**session["candidate_profile"])
    company_research = CompanyResearchResult(**session["company_research"])
    if not company_research.company_grading_rubric:
        company_research = await research_company_and_role(
            company_name=session["company_name"],
            target_role=session["target_role"],
            job_description=session["job_description"],
            experience_level=candidate_profile.experience_level,
        )

    evaluation = await evaluate_interview_answer(
        question_text=question["question_text"],
        question_category=question["category"],
        evaluation_focus=question.get("evaluation_focus", []),
        transcript_verbatim=verbatim,
        delivery_metrics=delivery_metrics,
        candidate_profile=candidate_profile,
        company_research=company_research,
        job_description=session["job_description"],
    )

    saved_attempt = save_question_attempt(
        session_id=session_id,
        question_id=question_id,
        duration_seconds=delivery_metrics.duration_seconds,
        stt_provider=stt["stt_provider"],
        transcript_verbatim=verbatim,
        transcript_clean=stt["transcript_clean"],
        word_timestamps=[w.model_dump() for w in timestamps],
        delivery_metrics=delivery_metrics.model_dump(),
        evaluation=evaluation.model_dump(),
        company_name=session["company_name"],
        target_role=session["target_role"],
    )
    return QuestionAttemptResponse(**saved_attempt)


class TTSRequest(BaseModel):
    text: str


@app.post("/api/tts")
async def text_to_speech(req: TTSRequest) -> Response:
    audio_bytes, mime = await synthesize_speech_bytes(req.text)
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="Neural TTS not configured; use browser Web Speech API.")
    return Response(content=audio_bytes, media_type=mime)


# ---------------------------------------------------------------------------
# Stage 5: Study Plan & Workspace Overview
# ---------------------------------------------------------------------------
@app.get("/api/study-plan", response_model=list[StudyPlanRecord])
def get_study_plan() -> list[StudyPlanRecord]:
    return [StudyPlanRecord(**item) for item in list_study_items()]


class StudyToggleRequest(BaseModel):
    completed: bool


@app.patch("/api/study-plan/{item_id}", response_model=StudyPlanRecord)
def update_study_item(item_id: str, req: StudyToggleRequest) -> StudyPlanRecord:
    updated = toggle_study_item(item_id, req.completed)
    if not updated:
        raise HTTPException(status_code=404, detail="Study item not found.")
    return StudyPlanRecord(**updated)


@app.get("/api/overview", response_model=OverviewStatsResponse)
def get_overview() -> OverviewStatsResponse:
    stats = get_overview_stats()
    llm_p, llm_m = settings.active_llm_info()
    stt_p, stt_m = settings.active_stt_info()
    tts_p, tts_m = settings.active_tts_info()
    return OverviewStatsResponse(
        **stats,
        active_llm={"provider": llm_p, "model": llm_m},
        active_stt={"provider": stt_p, "model": stt_m},
        active_tts={"provider": tts_p, "model": tts_m},
    )
