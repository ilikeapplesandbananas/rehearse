from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from config import BASE_DIR, settings
from models.schemas import CompanyResearchResult, ExplorePillar, InterviewRoundInfo
from services.database import get_cached_company_research, save_cached_company_research

logger = logging.getLogger(__name__)

_DATA_CACHE: dict[str, Any] | None = None


def _clean_dashes(text: str) -> str:
    cleaned = text.replace("\u2014", ", ").replace("\u2013", "-").replace("\ufffd", "-")
    cleaned = re.sub(r"\s+,\s+", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def load_intelligence_db(force_reload: bool = False) -> dict[str, Any]:
    global _DATA_CACHE
    if _DATA_CACHE is None or force_reload:
        path = BASE_DIR / "data" / "company_intelligence.json"
        _DATA_CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _DATA_CACHE


def normalize_company_key(company_name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]+", "", company_name.lower()).strip()
    cleaned = re.sub(
        r"\s+(inc|llc|ltd|pty|corp|corporation|technologies|tech|labs|group|co|sa|international)$",
        "",
        cleaned,
    ).strip()
    return re.sub(r"\s+", " ", cleaned)


def detect_role_key(target_role: str, job_description: str = "") -> str:
    db = load_intelligence_db()
    role_lower = target_role.lower()
    jd_lower = job_description[:500].lower()

    best_key = "backend"
    best_score = 0
    for r_key, r_info in db["roles"].items():
        score = 0
        for kw in r_info["keywords"]:
            if kw in role_lower:
                score = max(score, 100 + len(kw))
            elif kw in jd_lower:
                score = max(score, 20 + len(kw))
        if score > best_score:
            best_score = score
            best_key = r_key
    return best_key


def detect_seniority_track(
    target_role: str,
    experience_level: str = "",
    job_description: str = "",
) -> str:
    role_low = target_role.lower()
    exp_low = experience_level.lower()
    jd_low = job_description[:400].lower()

    if any(k in role_low for k in ["vac work", "vacation work", "holiday work", "winter school", "summer school", "vac student"]):
        return "vac_work"
    if any(k in role_low for k in ["senior", "staff", "principal", "lead", "head of", "architect"]):
        return "mid_senior"
    if any(k in role_low for k in ["intern", "graduate", "grad ", "bursary", "trainee", "junior", "entry"]):
        return "intern_grad"
    if any(k in exp_low for k in ["vac work", "vacation work"]):
        return "vac_work"
    if any(k in exp_low for k in ["student", "final-year", "grad", "intern", "learnership"]) and "senior" not in role_low:
        return "intern_grad"
    if any(k in jd_low for k in ["vacation work", "vac work"]):
        return "vac_work"
    if any(k in jd_low for k in ["internship", "graduate programme", "grad programme", "entry-level"]):
        return "intern_grad"
    return "junior"


def list_all_archetypes() -> list[dict[str, Any]]:
    db = load_intelligence_db()
    return list(db["archetypes"].values())


def list_known_companies() -> list[dict[str, str]]:
    db = load_intelligence_db()
    seen: set[str] = set()
    companies: list[dict[str, str]] = []

    for ov in db["company_overrides"].values():
        name = ov["display_name"]
        arch = db["archetypes"][ov["archetype_id"]]
        key = normalize_company_key(name)
        if key not in seen:
            seen.add(key)
            companies.append(
                {
                    "name": name,
                    "archetype_id": arch["id"],
                    "archetype_label": arch["short_label"],
                }
            )

    for arch in db["archetypes"].values():
        for name in arch["shared_companies"]:
            key = normalize_company_key(name)
            if key not in seen:
                seen.add(key)
                companies.append(
                    {
                        "name": name,
                        "archetype_id": arch["id"],
                        "archetype_label": arch["short_label"],
                    }
                )
    companies.sort(key=lambda x: x["name"].lower())
    return companies


def _find_curated_match(company_name: str) -> tuple[str | None, dict[str, Any] | None]:
    db = load_intelligence_db()
    key = normalize_company_key(company_name)
    raw_low = company_name.lower().strip()

    if key in db["company_overrides"]:
        override = db["company_overrides"][key]
        return override["archetype_id"], override
    if raw_low in db["company_overrides"]:
        override = db["company_overrides"][raw_low]
        return override["archetype_id"], override

    for ov_key, override in sorted(db["company_overrides"].items(), key=lambda kv: -len(kv[0])):
        if len(ov_key) <= 4:
            if re.search(rf"\b{re.escape(ov_key)}\b", key) or re.search(rf"\b{re.escape(ov_key)}\b", raw_low):
                return override["archetype_id"], override
        elif ov_key in key or key in ov_key or ov_key in raw_low:
            return override["archetype_id"], override

    for arch_id, arch in db["archetypes"].items():
        for shared in arch["shared_companies"]:
            s_key = normalize_company_key(shared)
            if s_key == key or (len(key) >= 4 and len(s_key) >= 4 and (s_key in key or key in s_key)):
                return arch_id, {
                    "display_name": shared,
                    "archetype_id": arch_id,
                    "nuances": [
                        f"Shares the '{arch['name']}' interview format used across {', '.join(arch['shared_companies'][:5])}."
                    ],
                }

    return None, None


def _classify_unknown_company_heuristic(company_name: str, job_description: str) -> str:
    text = f"{company_name} {job_description}".lower()
    if any(w in text for w in ["cyber", "security", "pentest", "soc", "infosec", "sensepost", "siem"]):
        return "cybersecurity_offense_defense"
    if any(w in text for w in ["kion", "dematic", "warehouse", "intralogistics", "plc", "robotics", "automation"]):
        return "industrial_automation_supply_chain"
    if any(w in text for w in ["south africa", "johannesburg", "cape town", "pretoria", "midrand", "sandton", "durban", "grad programme", "graduate programme", "vac work", "vacation work", "bursary"]):
        if any(w in text for w in ["consulting", "case study", "advisory", "transformation"]):
            return "consulting_vca_bi_case"
        if any(w in text for w in ["oop", ".net", "shesha", "java", "software house", "testgorilla", "gendac", "electrum", "vac work"]):
            return "sa_software_grad_consultancy"
        return "sa_enterprise_retail_bank_fintech"
    if any(w in text for w in ["payment", "fintech", "ledger", "banking", "checkout", "trading", "billing", "card", "kyc"]):
        return "pragmatic_fintech_api"
    if any(w in text for w in ["llm", "foundation model", "ai agent", "inference", "alignment", "generative ai", "gpu cluster"]):
        return "ai_frontier_lab"
    if any(w in text for w in ["quant", "low latency", "microsecond", "order book", "market making", "hft", "fpga"]):
        return "hft_quant_engineering"
    if any(w in text for w in ["observability", "database engine", "kernel", "storage engine", "edge network", "spark", "kafka", "data lake"]):
        return "systems_infra_data"
    if any(w in text for w in ["consulting", "business case", "vca", "advisory"]):
        return "consulting_vca_bi_case"
    if any(w in text for w in ["enterprise", "multi-tenant", "erp", "crm", "compliance", "saas platform"]):
        return "enterprise_platform"
    return "product_craft_scaleup"


def _synthesize_researched_jd(
    company_name: str,
    role_label: str,
    domain_context: str,
    role_info: dict[str, Any],
    seniority_track: str,
    grading_rubric: list[str],
) -> str:
    if seniority_track == "vac_work":
        level_intro = (
            f"Join {company_name}'s structured Vacation Work (Vac Work) programme inside our "
            f"{domain_context}. Work side-by-side with senior engineers and mentors on real production sprints."
        )
    elif seniority_track == "intern_grad":
        level_intro = (
            f"Join {company_name} as a {role_label} working across {domain_context}. "
            f"Contribute to production deliverables while ramping rapidly through mentorship and code/design reviews."
        )
    else:
        level_intro = (
            f"Join {company_name} as a {role_label} driving core initiatives across {domain_context}."
        )

    resp = role_info.get(
        "jd_responsibilities",
        "Design, implement, and verify reliable technical and analytical deliverables with strong cross-functional ownership.",
    )
    req = role_info.get(
        "jd_requirements",
        "Strong computer science, SQL/data, and problem-solving fundamentals with proven project ownership.",
    )
    bar_hint = grading_rubric[0] if grading_rubric else "Clear structured reasoning and measurable ownership"

    jd_text = (
        f"{level_intro}\n\n"
        f"Key Responsibilities: {resp}\n\n"
        f"Requirements & {company_name} Evaluation Bar: {req} Interviewers evaluate specifically for: {bar_hint}."
    )
    return _clean_dashes(jd_text)


def _smart_trim(text: str, max_len: int) -> str:
    clean = _clean_dashes(text).strip()
    if len(clean) <= max_len:
        return clean.rstrip(" .,:;/(")
    cut = clean[:max_len].rsplit(" ", 1)[0].strip()
    if cut.count("(") > cut.count(")"):
        cut = cut.rsplit("(", 1)[0].strip()
    return cut.rstrip(" .,:;/(-")


def _synthesize_explore_pillars(
    company_name: str,
    role_label: str,
    role_info: dict[str, Any],
    arch: dict[str, Any],
    seniority_track: str,
    coding_patterns: list[str],
    expected_structure: str,
) -> list[ExplorePillar]:
    short_role = role_label.split("(")[0].strip()
    if len(short_role) > 32:
        short_role = " ".join(short_role.split()[:3])

    if seniority_track == "vac_work":
        p1_title = "CV projects & curiosity"
        p1_desc = f"Thinking out loud on your university/GitHub projects, bugs fixed, and rapid learning at {company_name}."
    elif seniority_track == "intern_grad":
        p1_title = "Projects & problem solving"
        p1_desc = f"Deep probing on your CV projects, CS/data trade-offs, and how you debug under {company_name} standards."
    else:
        p1_title = "Architecture & ownership"
        p1_desc = f"Production scale choices, bottlenecks, and measurable system ownership in your {short_role} work."

    top_topic = role_info["core_topics"][0] if role_info.get("core_topics") else "Core technical & role execution"
    top_coding = coding_patterns[0] if coding_patterns else ""
    if top_coding and any(k in role_label.lower() or k in arch["id"] for k in ["software", "swe", "engineer", "dev", "vac", "grad", "dematic", "kion", "gendac", "electrum", "cyber", "bbd"]):
        coding_snippet = _smart_trim(top_coding, 78)
        p2_desc = _clean_dashes(f"{top_topic.split(':')[0]}. Coding focus: {coding_snippet}.")
    else:
        p2_desc = _clean_dashes(f"{_smart_trim(top_topic, 86)}.")

    p3_title = f"How {company_name} marks answers"
    p3_desc = _clean_dashes(f"{arch['short_label']} rubric: {_smart_trim(expected_structure, 105)}.")

    return [
        ExplorePillar(index="01", title=_clean_dashes(p1_title), description=_clean_dashes(p1_desc)),
        ExplorePillar(index="02", title=_clean_dashes(f"{short_role} core"), description=p2_desc),
        ExplorePillar(index="03", title=_clean_dashes(p3_title), description=p3_desc),
    ]


async def _fetch_live_web_snippets(company_name: str, target_role: str) -> list[str]:
    """Fetches real interview process context from Reddit/Glassdoor/Blind via Tavily or DuckDuckGo."""
    snippets: list[str] = []

    if settings.tavily_api_key:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": f"{company_name} {target_role} interview process rounds reddit glassdoor",
                        "max_results": 5,
                        "search_depth": "basic",
                    },
                )
                if r.status_code == 200:
                    for item in r.json().get("results", []):
                        content = _clean_dashes(item.get("content", ""))
                        title = _clean_dashes(item.get("title", ""))
                        if content:
                            snippets.append(f"{title}: {content[:300]}")
            if snippets:
                return snippets
        except Exception as exc:
            logger.debug("Tavily search failed: %s", exc)

    try:
        query = f"{company_name} {target_role} interview rounds reddit"
        async with httpx.AsyncClient(
            timeout=8.0,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
        ) as client:
            r = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
            if r.status_code == 200:
                raw_snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, flags=re.S)
                for s in raw_snips[:5]:
                    clean = re.sub(r"<[^>]+>", "", s)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    clean = _clean_dashes(clean)
                    if len(clean) > 40:
                        snippets.append(clean[:300])
    except Exception as exc:
        logger.debug("DuckDuckGo live snippet lookup skipped: %s", exc)

    return snippets


async def research_company_and_role(
    company_name: str,
    target_role: str,
    job_description: str = "",
    force_live: bool = False,
    experience_level: str = "",
) -> CompanyResearchResult:
    """
    Matches company + target role + seniority track against our deduplicated Tech Interview
    Knowledge Base (and live web search if unknown). Generates authentic researched job
    descriptions, seniority-aware rounds, LeetCode/coding patterns, and company-specific grading rubrics.
    """
    db = load_intelligence_db()
    norm_key = normalize_company_key(company_name) or "tech company"
    role_key = detect_role_key(target_role, job_description)
    role_info = db["roles"][role_key]
    role_label = _clean_dashes(target_role.strip() or role_info["label"])
    seniority_track = detect_seniority_track(role_label, experience_level, job_description)

    # 1. Check curated 50+ unique company intelligence database
    arch_id, override = _find_curated_match(company_name)
    if arch_id and not force_live:
        arch = db["archetypes"][arch_id]
        display = _clean_dashes(override["display_name"] if override else company_name.strip())
        peers = [c for c in arch["shared_companies"] if normalize_company_key(c) != normalize_company_key(display)]

        rounds_raw = (
            arch.get("intern_grad_rounds", arch["standard_rounds"])
            if seniority_track in {"vac_work", "intern_grad"}
            else arch["standard_rounds"]
        )

        # Deduplicated company-specific + archetype grading rubric
        rubric: list[str] = []
        for item in [*(override.get("company_grading_rubric", []) if override else []), *arch.get("company_grading_rubric", [])]:
            c_item = _clean_dashes(item)
            if c_item and c_item not in rubric:
                rubric.append(c_item)
        rubric = rubric[:5]

        expected_struct = _clean_dashes(
            (override.get("expected_answer_structure") if override else "")
            or arch.get("expected_answer_structure", "Situation & constraints -> Technical execution -> Trade-offs & impact")
        )

        coding_patterns: list[str] = []
        for cp in [*(override.get("coding_and_leetcode_patterns", []) if override else []), *arch.get("coding_and_leetcode_patterns", [])]:
            c_cp = _clean_dashes(cp)
            if c_cp and c_cp not in coding_patterns:
                coding_patterns.append(c_cp)
        coding_patterns = coding_patterns[:5]

        domain_context = _clean_dashes(
            (override.get("domain_context") if override else "")
            or f"technology and engineering teams in {arch['short_label']}"
        )

        researched_jd = _synthesize_researched_jd(
            company_name=display,
            role_label=role_label,
            domain_context=domain_context,
            role_info=role_info,
            seniority_track=seniority_track,
            grading_rubric=rubric,
        )

        explore_pillars = _synthesize_explore_pillars(
            company_name=display,
            role_label=role_label,
            role_info=role_info,
            arch=arch,
            seniority_track=seniority_track,
            coding_patterns=coding_patterns,
            expected_structure=expected_struct,
        )

        level_tag = "Vac Work / Intern" if seniority_track == "vac_work" else ("Intern / Graduate" if seniority_track == "intern_grad" else "Full-Time / Experienced")
        dedup_note = _clean_dashes(
            f"[{level_tag} track] Matches the {arch['short_label']} blueprint shared with {', '.join(peers[:4])}, "
            f"reusing proven rounds while calibrating grading for {display}'s {role_label} bar."
        )

        return CompanyResearchResult(
            company_name=display,
            normalized_key=norm_key,
            archetype_id=arch["id"],
            archetype_name=_clean_dashes(arch["name"]),
            archetype_short_label=_clean_dashes(arch["short_label"]),
            shared_companies=peers[:6],
            deduplication_note=dedup_note,
            summary=_clean_dashes(arch["summary"]),
            rounds=[InterviewRoundInfo(**r) for r in rounds_raw],
            company_nuances=[_clean_dashes(n) for n in (override.get("nuances", []) if override else [])],
            evaluation_bar=[_clean_dashes(e) for e in arch["evaluation_bar"]],
            role_key=role_key,
            role_label=role_label,
            role_core_topics=[_clean_dashes(t) for t in role_info["core_topics"]],
            seniority_track=seniority_track,
            researched_job_description=researched_jd,
            explore_pillars=explore_pillars,
            company_grading_rubric=rubric,
            expected_answer_structure=expected_struct,
            coding_and_leetcode_patterns=coding_patterns,
            role_grading_focus=[_clean_dashes(f) for f in role_info.get("role_grading_focus", [])],
            researched_live=False,
            sources=db["meta"]["sources"][:4],
        )

    # 2. Check local SQLite research cache for previously researched custom companies
    cache_key = f"{norm_key}::{role_key}::{seniority_track}"
    if not force_live:
        cached = get_cached_company_research(cache_key)
        if cached and cached.get("researched_job_description") and cached.get("company_grading_rubric"):
            return CompanyResearchResult(**cached)

    # 3. Live research + archetype classification for unknown company
    snippets = await _fetch_live_web_snippets(company_name, role_label)
    arch_id = _classify_unknown_company_heuristic(company_name, f"{job_description} {' '.join(snippets)}")
    arch = db["archetypes"][arch_id]
    display = _clean_dashes(company_name.strip())

    rounds_raw = (
        arch.get("intern_grad_rounds", arch["standard_rounds"])
        if seniority_track in {"vac_work", "intern_grad"}
        else arch["standard_rounds"]
    )
    rubric = [_clean_dashes(x) for x in arch.get("company_grading_rubric", arch["evaluation_bar"])][:4]
    expected_struct = _clean_dashes(
        arch.get("expected_answer_structure", "Context -> Technical approach -> Trade-offs & validation -> Impact")
    )
    coding_patterns = [_clean_dashes(x) for x in arch.get("coding_and_leetcode_patterns", [])][:4]

    nuances: list[str] = []
    if snippets:
        nuances.append(f"Live candidate signal found across web/Reddit reports for {display}:")
        for s in snippets[:2]:
            nuances.append(_clean_dashes(s))
    else:
        nuances.append(
            f"Based on the role profile, {display} aligns closely with the {arch['short_label']} interview loop."
        )
    nuances.append(
        f"Prep efficiency tip: mastering this {arch['short_label']} loop transfers directly to {', '.join(arch['shared_companies'][:4])}."
    )

    domain_context = (
        f"{arch['short_label'].lower()} initiatives ({snippets[0][:110]})"
        if snippets
        else f"{arch['short_label'].lower()} product, data, and software engineering systems"
    )
    researched_jd = _synthesize_researched_jd(
        company_name=display,
        role_label=role_label,
        domain_context=domain_context,
        role_info=role_info,
        seniority_track=seniority_track,
        grading_rubric=rubric,
    )
    explore_pillars = _synthesize_explore_pillars(
        company_name=display,
        role_label=role_label,
        role_info=role_info,
        arch=arch,
        seniority_track=seniority_track,
        coding_patterns=coding_patterns,
        expected_structure=expected_struct,
    )

    result = CompanyResearchResult(
        company_name=display,
        normalized_key=norm_key,
        archetype_id=arch["id"],
        archetype_name=_clean_dashes(arch["name"]),
        archetype_short_label=_clean_dashes(arch["short_label"]),
        shared_companies=arch["shared_companies"][:6],
        deduplication_note=_clean_dashes(
            f"Grouped into the {arch['short_label']} archetype (shared with {', '.join(arch['shared_companies'][:4])}) "
            f"so you focus on real high-signal questions instead of duplicate question banks."
        ),
        summary=_clean_dashes(arch["summary"]),
        rounds=[InterviewRoundInfo(**r) for r in rounds_raw],
        company_nuances=nuances,
        evaluation_bar=[_clean_dashes(e) for e in arch["evaluation_bar"]],
        role_key=role_key,
        role_label=role_label,
        role_core_topics=[_clean_dashes(t) for t in role_info["core_topics"]],
        seniority_track=seniority_track,
        researched_job_description=researched_jd,
        explore_pillars=explore_pillars,
        company_grading_rubric=rubric,
        expected_answer_structure=expected_struct,
        coding_and_leetcode_patterns=coding_patterns,
        role_grading_focus=[_clean_dashes(f) for f in role_info.get("role_grading_focus", [])],
        researched_live=bool(snippets),
        sources=["Live Web & Reddit Search", *db["meta"]["sources"][:3]] if snippets else db["meta"]["sources"][:3],
    )

    save_cached_company_research(cache_key, display, result.model_dump())
    return result
