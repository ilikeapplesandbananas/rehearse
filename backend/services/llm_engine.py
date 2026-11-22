from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel, Field

from config import settings
from models.schemas import (
    CandidateProfile,
    CompanyResearchResult,
    DeliveryMetrics,
    EvaluationResult,
    ExplorePillar,
    FeedbackGap,
    RubricScores,
    StudyMaterialItem,
)
from services.company_research import load_intelligence_db

logger = logging.getLogger(__name__)


def sanitize_clean_text(obj: Any) -> Any:
    """Recursively strips em dashes and en dashes so output typography stays clean and neat."""
    if isinstance(obj, str):
        cleaned = obj.replace("\u2014", ", ").replace("\u2013", "-").replace("\ufffd", "-")
        cleaned = re.sub(r"\s+,\s+", ", ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned
    if isinstance(obj, list):
        return [sanitize_clean_text(item) for item in obj]
    if isinstance(obj, dict):
        return {k: sanitize_clean_text(v) for k, v in obj.items()}
    return obj


class GeneratedQuestionItem(BaseModel):
    short_title: str
    category: str
    question_text: str
    source_attribution: str
    guidance_cues: list[str] = Field(min_length=3, max_length=3)
    evaluation_focus: list[str] = Field(default_factory=list)


class GeneratedInterviewPack(BaseModel):
    explore_pillars: list[ExplorePillar]
    questions: list[GeneratedQuestionItem]


async def _call_frontier_json(
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any] | None = None,
    temperature: float = 0.25,
) -> tuple[dict[str, Any] | None, str, str]:
    """
    Calls the strongest configured LLM with strict JSON output enforcement.
    Priority: Gemini cascade -> Anthropic Claude Sonnet 4 -> OpenAI GPT-4.1/4o.
    Returns (parsed_json_or_none, provider_name, actual_model_name).
    """
    provider, model = settings.active_llm_info()
    if provider == "local_coach":
        return None, provider, model

    used_model = model
    try:
        if provider == "gemini":
            raw, used_model = await _call_gemini(system_prompt, user_prompt, model, temperature)
        elif provider == "anthropic":
            raw = await _call_anthropic(system_prompt, user_prompt, model, temperature)
        elif provider == "openai":
            raw = await _call_openai(system_prompt, user_prompt, model, temperature)
        else:
            return None, "local_coach", "deterministic-rubric-v1"

        parsed = _extract_json_object(raw)
        if parsed is not None:
            return sanitize_clean_text(parsed), provider, used_model
        logger.warning("LLM %s returned non-JSON payload, retrying once with strict repair", provider)
        repair_prompt = (
            f"{user_prompt}\n\nIMPORTANT: Return ONLY a single valid JSON object with no markdown fences "
            f"or extra commentary."
        )
        if provider == "gemini":
            raw2, used_model = await _call_gemini(system_prompt, repair_prompt, used_model, 0.1)
        elif provider == "anthropic":
            raw2 = await _call_anthropic(system_prompt, repair_prompt, model, 0.1)
        else:
            raw2 = await _call_openai(system_prompt, repair_prompt, model, 0.1)
        repaired = _extract_json_object(raw2)
        return (sanitize_clean_text(repaired) if repaired else None), provider, used_model
    except Exception as exc:
        logger.warning("Frontier LLM (%s:%s) call failed: %s", provider, used_model, exc)
        return None, "local_coach", "deterministic-rubric-v1"


async def _call_gemini(
    system_prompt: str, user_prompt: str, model: str, temperature: float
) -> tuple[str, str]:
    cascade: list[str] = []
    for candidate in [
        model,
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite-preview",
        "gemma-4-31b-it",
        "gemma-4-26b-a4b-it",
    ]:
        if candidate and candidate not in cascade:
            cascade.append(candidate)

    params = {"key": settings.gemini_api_key}
    last_err: Exception | None = None

    for candidate_model in cascade:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent"
        is_gemma = candidate_model.startswith("gemma-")
        if is_gemma:
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_prompt}\n\n{user_prompt}\n\nRespond with valid JSON only."}],
                    }
                ],
                "generationConfig": {"temperature": temperature},
            }
        else:
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            }

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                r = await client.post(url, params=params, json=payload)
                if r.status_code >= 400:
                    logger.warning("Gemini model %s returned %s, trying next fallback", candidate_model, r.status_code)
                    last_err = RuntimeError(f"HTTP {r.status_code} from {candidate_model}")
                    continue
                data = r.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
            if text:
                return text, candidate_model
            last_err = RuntimeError(f"Empty output from {candidate_model}")
        except Exception as exc:
            logger.warning("Gemini model %s failed (%s), trying next fallback", candidate_model, exc)
            last_err = exc

    raise last_err or RuntimeError("All Gemini cascade models failed")


async def _call_anthropic(system_prompt: str, user_prompt: str, model: str, temperature: float) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4096,
        "temperature": temperature,
        "system": system_prompt + "\nRespond with valid JSON only.",
        "messages": [{"role": "user", "content": user_prompt}],
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


async def _call_openai(system_prompt: str, user_prompt: str, model: str, temperature: float) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
    return None


async def enrich_candidate_profile_with_llm(
    raw_text: str, heuristic_profile: CandidateProfile
) -> CandidateProfile:
    """Uses frontier LLM to refine extracted CV projects, skills, and seniority cleanly."""
    system_prompt = (
        "You are an expert technical recruiter extracting a structured candidate profile from a CV. "
        "Return strict JSON matching the requested schema. Never invent facts not present in the CV."
    )
    user_prompt = f"""Extract a clean structured candidate profile from this CV text.
Return JSON with keys:
- candidate_name (string)
- experience_level (short label like "Mid-level engineer", "Senior engineer", "Intern / Early-career")
- years_experience (short label like "4 years experience")
- primary_skills (array of 4-7 concise tech skills)
- projects (array of up to 4 objects: {{name, summary, technologies, scale_or_impact}})
- education (string)
- projects_summary_line (one crisp sentence like "Found 3 projects, including your real-time analytics platform.")

CV TEXT:
{raw_text[:8000]}
"""
    parsed, _, _ = await _call_frontier_json(system_prompt, user_prompt, temperature=0.1)
    if parsed:
        try:
            return CandidateProfile(**parsed)
        except Exception as exc:
            logger.debug("LLM CV profile schema mismatch, using heuristic: %s", exc)
    return heuristic_profile


async def generate_tailored_interview(
    candidate_profile: CandidateProfile,
    cv_raw_text: str,
    company_research: CompanyResearchResult,
    job_description: str,
    round_focus: str = "full_loop",
    question_count: int = 6,
) -> tuple[list[ExplorePillar], list[dict[str, Any]]]:
    """
    Generates 5-8 deeply realistic interview questions grounded in:
      1. The company's actual researched interview process & archetype
      2. The target tech role's specific rounds
      3. Specific projects and claims from the candidate's CV
      4. Key requirements from the pasted Job Description
    """
    system_prompt = (
        "You are a calibrated hiring-bar interviewer designing an authentic mock interview loop for a specific company "
        "and seniority level. Your questions must sound exactly like what interviewers actually ask in that company's "
        "real rounds for that role (whether Vacation Work, Intern, Graduate Programme, or Experienced). Cross-reference "
        "specific CV projects, experience, and skills against the company's researched rounds, LeetCode/coding patterns, "
        "case/security/PM scenarios, and Job Description. Never use em dashes or en dashes anywhere in your output. "
        "Keep punctuation clean and neat. Return strict JSON only."
    )

    projects_json = json.dumps([p.model_dump() for p in candidate_profile.projects], indent=2)
    rounds_json = json.dumps([r.model_dump() for r in company_research.rounds], indent=2)
    seniority_note = (
        "CRITICAL SENIORITY CALIBRATION: This candidate is applying for VACATION WORK / INTERNSHIP / GRADUATE PROGRAMME level "
        f"({company_research.seniority_track}). Calibrate technical depth to core CS/OOP/SQL, LeetCode Easy/Medium algorithm "
        "walkthroughs, debugging reasoning, learnability, thinking out loud, and deep probing on their actual CV projects rather "
        "than senior staff architecture buzzwords."
        if company_research.seniority_track in {"vac_work", "intern_grad"}
        else "SENIORITY CALIBRATION: Full-time / experienced engineering bar expecting independent ownership, system trade-offs, and production scale."
    )

    user_prompt = f"""Create a tailored {question_count}-question mock interview session.

TARGET COMPANY: {company_research.company_name}
TARGET ROLE: {company_research.role_label}
SENIORITY TRACK: {company_research.seniority_track}
INTERVIEW ARCHETYPE: {company_research.archetype_name}
SHARED WITH PEER COMPANIES: {", ".join(company_research.shared_companies)}
{seniority_note}

RESEARCHED INTERVIEW ROUNDS FOR THIS COMPANY:
{rounds_json}
COMPANY NUANCES (Reddit / Glassdoor / Portals):
{json.dumps(company_research.company_nuances, indent=2)}
COMPANY-TAGGED CODING / LEETCODE & TECHNICAL PATTERNS:
{json.dumps(company_research.coding_and_leetcode_patterns, indent=2)}
HOW THIS COMPANY MARKS ANSWERS (GRADING RUBRIC):
{json.dumps(company_research.company_grading_rubric, indent=2)}
EXPECTED ANSWER STRUCTURE:
{company_research.expected_answer_structure}
ROLE CORE TOPICS & GRADING FOCUS:
{json.dumps(company_research.role_core_topics + company_research.role_grading_focus, indent=2)}
SELECTED ROUND FOCUS: {round_focus}

CANDIDATE PROFILE:
- Name: {candidate_profile.candidate_name}
- Level: {candidate_profile.experience_level} ({candidate_profile.years_experience})
- Education: {candidate_profile.education}
- Skills: {", ".join(candidate_profile.primary_skills)}
- Work Experience: {json.dumps(candidate_profile.work_experience)}
- Projects: {projects_json}
- CV Excerpt: {cv_raw_text[:4000]}

JOB DESCRIPTION:
{job_description[:3000]}

REQUIREMENTS:
1. Generate exactly {question_count} questions mapped directly to the real rounds of {company_research.company_name} for {company_research.role_label}:
   - Q1: Sharp warm-up / background narrative tied specifically to {company_research.company_name} and why the candidate fits {company_research.role_label}.
   - Include at least 2 probing "Project deep dive" questions directly referencing REAL projects, tools, or internships on the candidate's CV (companies like Gendac, BBD, Electrum, KION, Stripe, and Amazon heavily test whether you truly built what your CV claims).
   - Include at least 1 spoken "Coding & algorithms" or role-authentic practical challenge grounded in {company_research.company_name}'s real test/LeetCode patterns ({", ".join(company_research.coding_and_leetcode_patterns[:2])}) asking the candidate to walk through their data structures, step-by-step logic, edge cases, and Big-O complexity (or SQL/CIRCLES/WBS/SIEM triage for non-coding roles).
   - Include realistic company-authentic technical/system/case questions and 1-2 company-calibrated "Behavioral" questions aligned with how {company_research.company_name} grades culture & ownership.
   - If round_focus is not "full_loop", weight 70% of questions toward that specific round ({round_focus}).
2. Also produce 3 concise "explore_pillars" (index "01", "02", "03") reflecting how {company_research.company_name} evaluates {company_research.role_label} candidates.
3. NEVER use em dashes or en dashes anywhere in any field.

RETURN STRICT JSON:
{{
  "explore_pillars": [
    {{"index": "01", "title": "...", "description": "..."}}
  ],
  "questions": [
    {{
      "short_title": "3-6 word queue title",
      "category": "Project deep dive | Coding & algorithms | System design | Technical depth | Case study | Behavioral | Warm-up",
      "question_text": "Natural spoken interview question (1-3 sentences, clear and probing)",
      "source_attribution": "e.g. Based on your CV  ·  Real-time analytics platform  OR  Real Electrum loop  ·  Thinking out loud coding",
      "guidance_cues": ["Short cue 1", "Short cue 2", "Short cue 3"],
      "evaluation_focus": ["Specific {company_research.company_name} marking criterion 1", "Criterion 2", "Criterion 3"]
    }}
  ]
}}
"""
    parsed, _, _ = await _call_frontier_json(system_prompt, user_prompt, temperature=0.35)
    if parsed and isinstance(parsed.get("questions"), list) and len(parsed["questions"]) >= 4:
        try:
            pack = GeneratedInterviewPack(**parsed)
            return pack.explore_pillars[:3], [q.model_dump() for q in pack.questions[:question_count]]
        except Exception as exc:
            logger.warning("Generated question pack validation failed, falling back: %s", exc)

    return _generate_local_tailored_interview(
        candidate_profile=candidate_profile,
        company_research=company_research,
        round_focus=round_focus,
        question_count=question_count,
    )


def _generate_local_tailored_interview(
    candidate_profile: CandidateProfile,
    company_research: CompanyResearchResult,
    round_focus: str,
    question_count: int,
) -> tuple[list[ExplorePillar], list[dict[str, Any]]]:
    db = load_intelligence_db()
    arch = db["archetypes"][company_research.archetype_id]
    company = company_research.company_name
    role = company_research.role_label
    lead_proj = (
        candidate_profile.projects[0].name
        if candidate_profile.projects
        else "your primary software or analytics project"
    )
    second_proj = (
        candidate_profile.projects[1].name
        if len(candidate_profile.projects) > 1
        else lead_proj
    )
    primary_skill = candidate_profile.primary_skills[0] if candidate_profile.primary_skills else "Python"
    db_skill = next(
        (s for s in candidate_profile.primary_skills if s.lower() in {"postgresql", "mysql", "mongodb", "redis", "dynamodb", "snowflake", "sql", "sqlite"}),
        "SQL / relational database",
    )

    def _clean_short_title(prefix: str, phrase: str, max_len: int = 34) -> str:
        full = f"{prefix} {phrase}".strip()
        if len(full) <= max_len:
            return full
        trimmed = full[:max_len].rsplit(" ", 1)[0]
        return trimmed or full[:max_len]

    pillars = (
        company_research.explore_pillars[:3]
        if company_research.explore_pillars
        else [
            ExplorePillar(
                index="01",
                title=_clean_short_title("Your", lead_proj.lower(), 30),
                description="Architecture, debugging, and the choices you made.",
            ),
            ExplorePillar(
                index="02",
                title=f"{role.split()[0]} fundamentals",
                description=company_research.role_core_topics[0][:62] + "."
                if company_research.role_core_topics
                else "Data structures, reliability, and practical trade-offs.",
            ),
            ExplorePillar(
                index="03",
                title=f"How {company} marks",
                description=f"{company_research.archetype_short_label} · {company_research.expected_answer_structure[:54]}.",
            ),
        ]
    )

    sig_qs = arch.get("signature_questions", [])
    q_sys = next((q for q in sig_qs if q["category"].lower() in {"system design", "case study"}), None) or (
        sig_qs[0]
        if sig_qs
        else {
            "category": "System design",
            "short_title": f"Design a core {company} system",
            "question": f"Design a resilient service core to {company}'s {role} team. Walk through data modeling, bottlenecks, and failure recovery.",
            "guidance": ["Start with scope & constraints", "Walk through architecture & data model", "Call out bottlenecks & trade-offs"],
        }
    )
    top_lc = company_research.coding_and_leetcode_patterns[0] if company_research.coding_and_leetcode_patterns else "Two Sum / Hash Map lookup (LeetCode 1)"
    q_code = next((q for q in sig_qs if "coding" in q["category"].lower()), None) or {
        "category": "Coding & algorithms",
        "short_title": f"{company} coding walkthrough",
        "question": f"Walk me out loud through solving a core {company} coding/technical pattern ({top_lc}). Explain your brute-force baseline first, how you optimize data structures and Big-O complexity, and which edge cases break naive solutions.",
        "guidance": ["State clarifying questions & brute force", "Walk through optimal data structure & Big-O", "Test edge cases out loud cleanly"],
    }
    q_tech = next((q for q in sig_qs if q["category"].lower() == "technical depth"), None) or (
        sig_qs[1]
        if len(sig_qs) > 1
        else {
            "category": "Technical depth",
            "short_title": "Data consistency & debugging",
            "question": f"How do you prevent race conditions and keep data consistent under concurrent requests in {db_skill}? Walk through your design.",
            "guidance": ["Define the exact race condition", "Compare isolation & locking strategies", "Discuss latency vs. safety trade-offs"],
        }
    )
    q_behav = next((q for q in sig_qs if "behavioral" in q["category"].lower()), None) or {
        "category": "Behavioral",
        "short_title": f"{company} ownership & teamwork",
        "question": f"Tell me about a time you hit a hard blocker or competing deadline while working on a project. What did YOU specifically do to resolve it, and what did you learn?",
        "guidance": ["Set Situation & Task in 30 seconds", "Focus on YOUR actions and trade-offs", "Close with quantified impact"],
    }

    bar_focus = company_research.company_grading_rubric[:3] or company_research.evaluation_bar[:3]

    questions: list[dict[str, Any]] = [
        {
            "short_title": "Tell me about yourself",
            "category": "Warm-up",
            "question_text": f"Walk me through your background as a {candidate_profile.experience_level.lower()}, why {company}'s {role} role stands out to you, and one project you are proudest of shipping.",
            "source_attribution": f"Real {company} loop  ·  Opening calibration",
            "guidance_cues": [
                "Connect your arc to this exact role in 90 seconds",
                "Spotlight one measurable win from your CV",
                f"Tie your skills to what {company} actually builds",
            ],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": q_code["short_title"],
            "category": q_code["category"],
            "question_text": q_code["question"],
            "source_attribution": f"Real {company} loop  ·  Coding / LeetCode round",
            "guidance_cues": q_code["guidance"][:3],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": _clean_short_title("Deep dive:", lead_proj, 34),
            "category": "Project deep dive",
            "question_text": f"Tell me how you designed and tested {lead_proj}. Walk me through a concrete bottleneck or tricky bug you hit and why you made the architectural choices you did.",
            "source_attribution": f"Based on your CV  ·  {lead_proj}",
            "guidance_cues": [
                "Give a 30-sec system overview first",
                "Explain your exact technical/data trade-offs",
                "Close with measured results and lessons learned",
            ],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": q_sys["short_title"],
            "category": q_sys["category"],
            "question_text": q_sys["question"],
            "source_attribution": f"{company} · {company_research.archetype_short_label} round",
            "guidance_cues": q_sys["guidance"][:3],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": q_behav["short_title"],
            "category": q_behav["category"],
            "question_text": q_behav["question"],
            "source_attribution": f"Real {company} loop  ·  Culture & ownership bar",
            "guidance_cues": q_behav["guidance"][:3],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": "A decision you would revisit",
            "category": "Project deep dive",
            "question_text": f"Looking back at {second_proj} with {primary_skill}, what is one implementation or data modeling choice you would redesign today if usage grew 10x?",
            "source_attribution": f"Based on your CV  ·  Engineering judgment probe",
            "guidance_cues": [
                "Name the original constraint honestly",
                "Identify what breaks first at 10x load",
                "Explain the clean improvement you would build today",
            ],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": q_tech["short_title"],
            "category": q_tech["category"],
            "question_text": q_tech["question"],
            "source_attribution": f"{company} · {role} technical bar",
            "guidance_cues": q_tech["guidance"][:3],
            "evaluation_focus": bar_focus,
        },
        {
            "short_title": "Debugging a live incident",
            "category": "Technical depth",
            "question_text": f"Suppose a critical workflow owned by {company}'s {role} team starts failing intermittently for 5% of users without a recent deploy. Walk me through your first 15 minutes of investigation.",
            "source_attribution": f"{company} · Production triage signal",
            "guidance_cues": [
                "Check blast radius, logs, and metrics first",
                "Narrow hypotheses systematically across app, DB, and network",
                "Explain safe mitigation before permanent fix",
            ],
            "evaluation_focus": bar_focus,
        },
    ]

    # Prioritize by round_focus if user picked a single round type
    if round_focus == "system_design":
        questions.sort(key=lambda q: 0 if "system" in q["category"].lower() or "deep dive" in q["category"].lower() else 1)
    elif round_focus == "behavioral":
        questions.sort(key=lambda q: 0 if "behavioral" in q["category"].lower() or "warm-up" in q["category"].lower() else 1)
    elif round_focus == "project_deep_dive":
        questions.sort(key=lambda q: 0 if "deep dive" in q["category"].lower() else 1)
    elif round_focus == "technical_depth":
        questions.sort(key=lambda q: 0 if any(k in q["category"].lower() for k in ["coding", "technical", "case"]) else 1)

    return pillars, questions[:question_count]


def _make_study_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


async def evaluate_interview_answer(
    question_text: str,
    question_category: str,
    evaluation_focus: list[str],
    transcript_verbatim: str,
    delivery_metrics: DeliveryMetrics,
    candidate_profile: CandidateProfile,
    company_research: CompanyResearchResult,
    job_description: str,
) -> EvaluationResult:
    """
    Multi-dimensional strict-JSON LLM evaluation combining:
      - Company-specific grading rubric & expected answer structure
      - Role-specific expectations & seniority calibration (Vac Work/Intern/Grad vs Full-Time)
      - Verbatim transcript + Python vocal telemetry (WPM, fillers/min, pauses >=2.5s, hedging)
      - Candidate CV context & Job Description requirements
    """
    system_prompt = (
        f"You are a calibrated hiring-bar interviewer at {company_research.company_name} evaluating a spoken answer for "
        f"{company_research.role_label} (seniority track: {company_research.seniority_track}). "
        "CRITICAL RULE: Do NOT grade generically. Grade strictly according to what THIS specific company and role look for "
        "in their real rubric and expected answer structure. An answer that lacks the exact structure or signals valued by "
        f"{company_research.company_name} (for example, failing to think out loud at Electrum/Gendac, lacking 'I' + metrics "
        "in Amazon LPs, omitting idempotency/edge cases at Stripe, listing automated tools without manual methodology at "
        "Orange Cyberdefense/SensePost, or missing Big-O/grid constraints at KION/Google) must be called out specifically by name. "
        "Do NOT inflate scores: vague, short, or unstructured answers score 40-65; solid answers score 70-84; truly strong "
        f"answers meeting {company_research.company_name}'s bar score 85-95. Use BOTH content AND voice telemetry (WPM, fillers/min, "
        "awkward pauses >=2.5s, hedging). Never use em dashes or en dashes anywhere. Return strict JSON only."
    )

    user_prompt = f"""Evaluate this spoken mock interview answer specifically against {company_research.company_name}'s marking standard.

COMPANY: {company_research.company_name} ({company_research.archetype_name})
ROLE: {company_research.role_label} (Seniority track: {company_research.seniority_track})
HOW {company_research.company_name.upper()} MARKS ANSWERS (COMPANY GRADING RUBRIC):
{json.dumps(company_research.company_grading_rubric or company_research.evaluation_bar, indent=2)}
EXPECTED ANSWER STRUCTURE FOR THIS COMPANY & ROLE:
{company_research.expected_answer_structure or "Clarify scope -> Technical/STAR execution -> Edge cases & trade-offs -> Measured outcome"}
ROLE-SPECIFIC GRADING FOCUS ({company_research.role_label}):
{json.dumps(company_research.role_grading_focus, indent=2)}
COMPANY EVALUATION BAR: {json.dumps(company_research.evaluation_bar)}

QUESTION CATEGORY: {question_category}
QUESTION ASKED: {question_text}
KEY SIGNALS EXPECTED FOR THIS QUESTION: {json.dumps(evaluation_focus)}

CANDIDATE CV CONTEXT:
- Level: {candidate_profile.experience_level} ({candidate_profile.years_experience})
- Skills: {", ".join(candidate_profile.primary_skills)}
- Projects: {json.dumps([p.model_dump() for p in candidate_profile.projects])}

JOB DESCRIPTION EXCERPT:
{job_description[:1600]}

COMPUTED VOICE DELIVERY SIGNALS (from verbatim STT):
- Duration: {delivery_metrics.duration_formatted} ({delivery_metrics.duration_seconds}s)
- Word count: {delivery_metrics.word_count}
- Speaking pace: {delivery_metrics.speaking_pace_wpm} WPM ({delivery_metrics.pace_label})
- Filler words: {delivery_metrics.filler_count} total ({delivery_metrics.filler_per_min}/min, {delivery_metrics.filler_label}) - breakdown: {json.dumps(delivery_metrics.filler_breakdown)}
- Longest pause: {delivery_metrics.longest_pause_sec}s ({delivery_metrics.pause_label}); awkward pauses >=2.5s: {len(delivery_metrics.awkward_pauses)}
- Auto-detected hedging phrases: {json.dumps(delivery_metrics.hedging_phrases)}

VERBATIM ANNOTATED TRANSCRIPT:
\"\"\"
{delivery_metrics.annotated_transcript or transcript_verbatim}
\"\"\"

RETURN STRICT JSON MATCHING THIS EXACT SCHEMA:
{{
  "headline": "Short encouraging editorial 5-7 word headline (e.g. 'Good foundation for {company_research.company_name}. Sharpen structure.')",
  "scores": {{
    "communication": 0-100,
    "communication_note": "3-5 word crisp note (e.g. 'Clear, with a few detours')",
    "technical_depth": 0-100,
    "technical_depth_note": "3-5 word crisp note referencing {company_research.company_name} bar",
    "structure": 0-100,
    "structure_note": "3-5 word crisp note on expected structure fit",
    "confidence": 0-100,
    "confidence_note": "3-5 word crisp note (e.g. 'Some hesitation signals')",
    "overall": 0-100
  }},
  "gaps": [
    {{"index": "01", "title": "Short actionable gap title", "detail": "1 crisp sentence diagnosing what {company_research.company_name} interviewers would mark down."}},
    {{"index": "02", "title": "Short actionable gap title", "detail": "1 crisp sentence naming the missing role/company rubric requirement or metric."}}
  ],
  "what_went_wrong": "Concrete diagnosis explicitly referencing {company_research.company_name}'s grading standard and structure.",
  "what_was_missing": "Specific technical depth, Big-O/LeetCode edge cases, security/PM/VCA framework, metrics, or company-specific signal omitted.",
  "how_to_fix": "Actionable coaching tailored to {company_research.company_name}'s {company_research.role_label} interview.",
  "fix_formula": "Ultra-concise arrow formula matching {company_research.company_name}'s expected answer structure",
  "sample_strong_answer": "Full natural spoken example rewrite meeting {company_research.company_name}'s exact bar using the candidate's CV context.",
  "sample_paragraphs": [
    "Paragraph 1 starting with opening quote mark matching {company_research.company_name}'s preferred opening...",
    "Paragraph 2 diving into trade-offs, complexity, edge cases, or STAR actions...",
    "Paragraph 3 closing with quantified impact and closing quote mark."
  ],
  "hedging_phrases_found": ["exact hedging phrases detected in transcript"],
  "study_material": [
    {{
      "topic": "Short crisp topic title",
      "subtitle": "Specific subtopic tailored to {company_research.company_name} & {company_research.role_label}",
      "why": "1 concise sentence explaining how this closes the gap in their answer.",
      "search_query_or_resource": "Exact high-signal resource or search query"
    }}
  ]
}}
"""
    parsed, provider, model = await _call_frontier_json(system_prompt, user_prompt, temperature=0.2)
    if parsed:
        try:
            for sm in parsed.get("study_material", []):
                if not sm.get("resource_url"):
                    sm["resource_url"] = _make_study_url(sm.get("search_query_or_resource") or sm.get("topic", ""))
            if not parsed.get("sample_paragraphs") and parsed.get("sample_strong_answer"):
                paras = [p.strip() for p in str(parsed["sample_strong_answer"]).split("\n\n") if p.strip()]
                parsed["sample_paragraphs"] = paras[:3]
            parsed["llm_provider"] = provider
            parsed["llm_model"] = model
            return EvaluationResult(**parsed)
        except Exception as exc:
            logger.warning("LLM evaluation schema mismatch, falling back to local coach: %s", exc)

    return _evaluate_answer_locally(
        question_text=question_text,
        question_category=question_category,
        transcript_verbatim=transcript_verbatim,
        delivery_metrics=delivery_metrics,
        candidate_profile=candidate_profile,
        company_research=company_research,
    )


def _evaluate_answer_locally(
    question_text: str,
    question_category: str,
    transcript_verbatim: str,
    delivery_metrics: DeliveryMetrics,
    candidate_profile: CandidateProfile,
    company_research: CompanyResearchResult,
) -> EvaluationResult:
    """High-signal deterministic company- and role-calibrated rubric coach."""
    text = transcript_verbatim.strip()
    lower = text.lower()
    wc = delivery_metrics.word_count

    tech_terms = [
        "latency", "throughput", "p95", "p99", "index", "partition", "shard", "queue", "kafka", "redis",
        "cache", "lock", "mvcc", "isolation", "idempoten", "consistency", "transaction", "o(", "complexity",
        "bottleneck", "trade-off", "tradeoff", "scale", "replica", "failover", "backpressure", "batch",
        "retry", "dead-letter", "schema", "postgres", "memory", "concurrency", "async", "metric", "slo",
        "webhook", "rate limit", "token bucket", "acid", "distributed", "observability",
        "solid", "oop", "polymorphism", "encapsulation", "interface", "bfs", "dfs", "hash map",
        "mitre", "owasp", "bola", "idor", "siem", "popia", "critical path", "wbs", "circles", "star schema", "dax",
    ]
    tech_hits = sum(1 for t in tech_terms if t in lower)
    has_numbers = bool(re.search(r"\b\d+(?:%|ms|s|x|k|m|gb|mb|rps|qps)?\b", lower))
    has_structure_markers = sum(
        1 for m in ["first", "second", "then", "finally", "started", "result", "impact", "trade-off", "because", "overview"]
        if m in lower
    )

    if wc < 20:
        tech_score = 44
        struct_score = 48
        comm_score = 52
    else:
        tech_score = min(92, max(48, 52 + tech_hits * 5 + (7 if has_numbers else 0)))
        struct_score = min(92, max(54, 60 + has_structure_markers * 6 + (6 if wc >= 75 else 0)))
        comm_score = 80
        if delivery_metrics.speaking_pace_wpm > 175 or (0 < delivery_metrics.speaking_pace_wpm < 98):
            comm_score -= 10
        if delivery_metrics.filler_per_min > 4.5:
            comm_score -= 8
        elif delivery_metrics.filler_per_min > 2.5:
            comm_score -= 4
        if wc < 55:
            comm_score -= 8
        comm_score = min(94, max(48, comm_score))

    conf_score = 84
    conf_score -= min(18, int(delivery_metrics.filler_per_min * 2.5))
    if delivery_metrics.longest_pause_sec >= 2.5:
        conf_score -= 8
    conf_score -= min(14, len(delivery_metrics.hedging_phrases) * 5)
    if delivery_metrics.speaking_pace_wpm > 175 or (0 < delivery_metrics.speaking_pace_wpm < 95):
        conf_score -= 6
    conf_score = min(94, max(45, conf_score))

    overall = int(round(0.25 * comm_score + 0.35 * tech_score + 0.20 * struct_score + 0.20 * conf_score))

    comm_note = "Clear and well-paced" if comm_score >= 82 else ("Clear, with a few detours" if comm_score >= 68 else "Tighten pacing and clarity")
    tech_note = f"Strong {company_research.company_name} bar" if tech_score >= 82 else ("Go deeper on trade-offs" if tech_score >= 62 else "Add concrete mechanics")
    struct_note = "A logical progression" if struct_score >= 76 else "Match company structure earlier"
    conf_note = "Composed, steady delivery" if conf_score >= 80 else ("Some hesitation signals" if conf_score >= 65 else "Reduce fillers & hedging")

    headline = (
        f"Strong fit for {company_research.company_name}."
        if overall >= 80
        else (f"Good start for {company_research.company_name}. Sharpen structure." if overall >= 66 else f"Tighten depth for {company_research.company_name}'s bar.")
    )

    is_behavioral = "behavioral" in question_category.lower() or "warm-up" in question_category.lower()
    primary_rubric = (
        company_research.company_grading_rubric[0]
        if company_research.company_grading_rubric
        else (company_research.evaluation_bar[0] if company_research.evaluation_bar else "Clear technical depth and personal ownership")
    )
    expected_struct = (
        company_research.expected_answer_structure
        or "30-sec context -> technical/action core -> edge cases -> quantified outcome"
    )

    if is_behavioral:
        gap1_title = "Tighten the opening setup"
        gap1_detail = f"Spend under 30 seconds framing context so you hit {company_research.company_name}'s expected structure: {expected_struct}."
        gap2_title = f"Hit {company_research.company_name}'s marking bar"
        gap2_detail = f"Interviewers at {company_research.company_name} grade specifically for: {primary_rubric}."
        fix_formula = expected_struct
        what_wrong = gap1_detail
        what_missing = gap2_detail
        how_to_fix = f"Structure tightly as ({expected_struct}), own your personal 'I' decisions, and quantify the final outcome."
        sample_paras = [
            f"\"When our project hit a critical delivery bottleneck ahead of deadline, I owned the root-cause diagnosis and cross-functional plan aligned with {company_research.role_label} standards.",
            f"Rather than pushing an untested shortcut, I structured our options, implemented clean automated validation, and documented trade-offs clearly for stakeholders.",
            "Within one sprint we shipped cleanly with zero regressions and cut manual effort by 40%, a habit I now enforce from kickoff.\"",
        ]
        study_items = [
            StudyMaterialItem(
                topic=f"{company_research.company_name} behavioral rubric",
                subtitle=f"{company_research.role_label}: STAR & individual ownership",
                why=f"Aligns your storytelling directly to what {company_research.company_name} graders mark positively.",
                search_query_or_resource=f"{company_research.company_name} {company_research.role_label} interview questions evaluation criteria",
                resource_url=_make_study_url(f"{company_research.company_name} {company_research.role_label} interview questions"),
            ),
            StudyMaterialItem(
                topic="Concise vocal delivery",
                subtitle="Replacing filler words with deliberate 1-second pauses",
                why="Directly lifts your Confidence and Communication sub-scores under pressure.",
                search_query_or_resource="technical interview communication pacing eliminate filler words",
                resource_url=_make_study_url("technical interview communication pacing eliminate filler words"),
            ),
        ]
    else:
        lead_proj = candidate_profile.projects[0].name if candidate_profile.projects else "the platform"
        gap1_title = f"Follow {company_research.company_name}'s flow"
        gap1_detail = f"Open with a crisp high-level frame before diving into code/metrics ({expected_struct})."
        gap2_title = "Address company-specific edge cases"
        gap2_detail = f"{company_research.company_name} interviewers specifically look for: {primary_rubric}."
        fix_formula = expected_struct
        what_wrong = gap1_detail
        what_missing = gap2_detail
        how_to_fix = f"Follow {company_research.company_name}'s structure ({expected_struct}) and explicitly compare complexity, edge cases, and failure recovery."
        sample_paras = [
            f"\"At {company_research.company_name}, I would first clarify throughput, correctness, and edge-case constraints before choosing the core model or data structures.",
            f"Building on experience from {lead_proj}, I would walk out loud from a clean baseline to the optimal solution, explicitly defending locking, O(N log K)/O(N) trade-offs, and safe failure handling.",
            "Finally, I would dry-run boundary cases and monitor p95 latency, correctness alerts, and business KPIs after rollout.\"",
        ]
        study_query = (
            company_research.coding_and_leetcode_patterns[0]
            if company_research.coding_and_leetcode_patterns
            else f"{company_research.company_name} {company_research.role_label} technical interview"
        )
        study_items = [
            StudyMaterialItem(
                topic=f"{company_research.company_name} technical bar",
                subtitle=f"{company_research.role_label}: {study_query[:48]}",
                why=f"Targets the exact pattern tested in {company_research.company_name}'s {company_research.role_label} round.",
                search_query_or_resource=study_query,
                resource_url=_make_study_url(study_query),
            ),
            StudyMaterialItem(
                topic="Edge cases & trade-off articulation",
                subtitle=f"{company_research.archetype_short_label} rubric",
                why="Prepares you to defend complexity, security, and failure boundaries out loud.",
                search_query_or_resource=f"{company_research.company_name} {company_research.role_label} interview preparation",
                resource_url=_make_study_url(f"{company_research.company_name} {company_research.role_label} interview preparation"),
            ),
        ]

    return sanitize_clean_text(
        EvaluationResult(
            headline=headline,
            scores=RubricScores(
                communication=comm_score,
                communication_note=comm_note,
                technical_depth=tech_score,
                technical_depth_note=tech_note,
                structure=struct_score,
                structure_note=struct_note,
                confidence=conf_score,
                confidence_note=conf_note,
                overall=overall,
            ),
            gaps=[
                FeedbackGap(index="01", title=gap1_title, detail=gap1_detail),
                FeedbackGap(index="02", title=gap2_title, detail=gap2_detail),
            ],
            what_went_wrong=what_wrong,
            what_was_missing=what_missing,
            how_to_fix=how_to_fix,
            fix_formula=fix_formula,
            sample_strong_answer="\n\n".join(sample_paras),
            sample_paragraphs=sample_paras,
            hedging_phrases_found=delivery_metrics.hedging_phrases,
            study_material=study_items,
            llm_provider="local_coach",
            llm_model="deterministic-rubric-v1",
        )
    )
