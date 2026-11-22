from __future__ import annotations

import base64
import io
import json
import logging
import re
from typing import Any, Tuple

import httpx
from docx import Document
from PIL import Image
from pypdf import PdfReader

from config import settings
from data.cv_presets import CV_PRESETS
from models.schemas import CandidateProfile, ProjectHighlight

logger = logging.getLogger(__name__)

SAMPLE_CV_TEXT = CV_PRESETS["stripe_data_analyst"]["raw_text"]

KNOWN_TECH_SKILLS = [
    "Python", "SQL", "TypeScript", "JavaScript", "Java", "C++", "C#", ".NET", "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin",
    "React", "Next.js", "Next.js 15", "Vue", "Angular", "Node.js", "FastAPI", "Flask", "Django", "Spring Boot", "ASP.NET",
    "PostgreSQL", "MySQL", "SQLite", "SQL Server", "MongoDB", "Redis", "Qdrant", "DynamoDB", "Snowflake", "BigQuery",
    "Power BI", "DAX", "Power Query", "Star Schema", "Tableau", "Excel", "ProjectLibre", "Shesha", "Jira", "Scrum",
    "PyTorch", "ONNX", "Scikit-learn", "TensorFlow", "LLMs", "RAG", "LangChain", "OpenCV", "Pandas",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "OpenShift", "Linux", "Terraform", "CI/CD", "PLC", "SCADA",
    "REST APIs", "GraphQL", "gRPC", "Kafka", "RabbitMQ", "Spark", "dbt", "NumPy", "Pytest", "Selenium", "Playwright",
    "WebSockets", "Tailwind CSS", "Git", "TCP/IP", "DNS", "DHCP", "POPIA", "CSPRNG", "OWASP", "SIEM", "Burp Suite", "Wireshark", "Nmap",
]

SECTION_PATTERNS = {
    "SUMMARY": r"^(?:PROFESSIONAL SUMMARY|PROFILE SUMMARY|EXECUTIVE SUMMARY|CAREER OBJECTIVE|CAREER SUMMARY|PERSONAL STATEMENT|SUMMARY|OBJECTIVE|PROFILE|ABOUT ME)$",
    "PROJECTS": r"^(?:[A-Z0-9,&/\- ]*\bPROJECTS?(?:\s+EXPERIENCE|\s*&\s*PORTFOLIO)?|PROJECT\s+EXPERIENCE)$",
    "EDUCATION": r"^(?:EDUCATION(?:\s*&\s*(?:ACCREDITED?\s*TRAINING|ACCREDITATION|QUALIFICATIONS|CERTIFICATIONS))?|ACADEMIC\s+(?:BACKGROUND|QUALIFICATIONS|RECORD)|QUALIFICATIONS)$",
    "SKILLS": r"^(?:[A-Z0-9,&/\- ]*\b(?:SKILLS|COMPETENCIES)|TECHNICAL\s+STACK)$",
    "EXPERIENCE": r"^(?:[A-Z0-9,&/\- ]*\bEXPERIENCE|EMPLOYMENT(?:\s+HISTORY)?|CAREER\s+HISTORY|WORK\s+HISTORY|INTERNSHIPS)$",
    "CERTIFICATIONS": r"^(?:CERTIFICATIONS(?:\s*&\s*TRAINING)?|CERTIFICATES|LICENSES\s*&\s*CERTIFICATIONS|COURSES\s*&\s*CERTIFICATIONS|AWARDS\s*&\s*CERTIFICATIONS)$",
    "LEADERSHIP": r"^(?:LEADERSHIP\b.*|UNIVERSITY\s+LEADERSHIP\b.*|ACTIVITIES\s*&\s*LEADERSHIP\b.*|COMMUNITY\b.*)$",
}


def sanitize_dashes(text: str) -> str:
    return (
        text.replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\ufffd", "-")
        .replace("  -  ", " - ")
    )


def normalize_cv_text(raw_text: str) -> str:
    """Normalizes OCR line breaks, replacement glyphs, and inline section headers like an ATS parser."""
    text = sanitize_dashes(raw_text or "")
    # Split inline section keywords such as "EDUCATION BSc..." or "PROJECT EXPERIENCE Lowkey AI..."
    inline_headers = [
        "PROFESSIONAL SUMMARY",
        "PROFILE SUMMARY",
        "EDUCATION & ACCREDITATION",
        "EDUCATION & ACCREDITED TRAINING",
        "EDUCATION",
        "COMPETENCIES & TECHNICAL SKILLS",
        "WORK EXPERIENCE",
        "PROJECT EXPERIENCE",
        "CERTIFICATIONS",
        "CERTIFICATES",
    ]
    for hdr in inline_headers:
        text = re.sub(
            rf"(?m)^({re.escape(hdr)})\s+([A-Z])",
            r"\1\n\2",
            text,
        )
    # Split rare inline project boundary like "operations. Library Management System | Java, OOP"
    text = re.sub(
        r"\.\s+([A-Z][A-Za-z0-9 &:\-]{3,55}\s*\|\s*[A-Za-z0-9, +.#/\-]+)",
        r".\n\1",
        text,
    )
    return text


def render_pdf_pages_to_png_base64(content: bytes, max_pages: int = 4) -> list[str]:
    """Renders PDF pages to crisp PNGs via pypdfium2 so Computer Vision reads visual layout directly."""
    images_b64: list[str] = []
    try:
        import pypdfium2 as pdfium  # type: ignore

        doc = pdfium.PdfDocument(content)
        total = min(len(doc), max_pages)
        for i in range(total):
            page = doc[i]
            bitmap = page.render(scale=135 / 72)
            pil_img = bitmap.to_pil()
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG", optimize=True)
            images_b64.append(base64.b64encode(buf.getvalue()).decode("ascii"))
        doc.close()
    except Exception as exc:
        logger.debug("PDF to PNG rendering skipped: %s", exc)
    return images_b64


def extract_text_and_images_from_upload(
    filename: str, content: bytes
) -> Tuple[str, str, int, list[str]]:
    """
    Returns (raw_text, file_type, page_count, page_images_b64).
    Supports PDF (text + Computer Vision page images), DOCX, TXT, and direct CV images (PNG/JPG/WEBP).
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text, pages = _extract_pdf(content)
        images = render_pdf_pages_to_png_base64(content, max_pages=4)
        return text, "PDF", pages, images

    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        img = Image.open(io.BytesIO(content)).convert("RGB")
        img.thumbnail((1600, 2200))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return "[Image CV scanned with Computer Vision]", "IMG", 1, [b64]

    if lower.endswith(".docx"):
        text, pages = _extract_docx(content)
        return text, "DOCX", pages, []

    text = content.decode("utf-8", errors="ignore").strip()
    pages = max(1, len(text) // 2600 + 1)
    return text, "TXT", pages, []


def extract_text_from_upload(filename: str, content: bytes) -> Tuple[str, str, int]:
    text, ftype, pages, _ = extract_text_and_images_from_upload(filename, content)
    return text, ftype, pages


def _extract_pdf(content: bytes) -> Tuple[str, int]:
    try:
        import pdfplumber  # type: ignore

        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            page_count = max(1, len(pdf.pages))
            for page in pdf.pages:
                t = page.extract_text(layout=False) or ""
                if t.strip():
                    pages_text.append(t.strip())
        combined = "\n\n".join(pages_text).strip()
        if combined:
            return combined, page_count
    except Exception:
        pass

    reader = PdfReader(io.BytesIO(content))
    page_count = max(1, len(reader.pages))
    chunks = [(p.extract_text() or "").strip() for p in reader.pages]
    combined = "\n\n".join(c for c in chunks if c).strip()
    return combined, page_count


def _extract_docx(content: bytes) -> Tuple[str, int]:
    doc = Document(io.BytesIO(content))
    lines: list[str] = []
    for p in doc.paragraphs:
        if p.text.strip():
            lines.append(p.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_txt:
                lines.append(row_txt)
    combined = "\n".join(lines).strip()
    est_pages = max(1, len(combined) // 2600 + 1)
    return combined, est_pages


def _segment_ats_sections(raw_text: str) -> dict[str, list[str]]:
    normalized = normalize_cv_text(raw_text)
    sections: dict[str, list[str]] = {
        "HEADER": [],
        "SUMMARY": [],
        "EDUCATION": [],
        "SKILLS": [],
        "EXPERIENCE": [],
        "PROJECTS": [],
        "CERTIFICATIONS": [],
        "LEADERSHIP": [],
    }
    current = "HEADER"
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched_sec = None
        # Match BOTH uppercase ATS headings and concise Title Case headings across all CV styles
        if len(line) <= 72 and "|" not in line and not line.startswith(("•", "-", "*")):
            alpha = [c for c in line if c.isalpha()]
            mostly_upper = bool(alpha) and sum(1 for c in alpha if c.isupper()) >= len(alpha) * 0.85
            concise_title = len(line.split()) <= 5 and not line.endswith(".") and line[:1].isupper()
            if mostly_upper or concise_title:
                for sec_name, pat in SECTION_PATTERNS.items():
                    if re.match(pat, line, flags=re.I):
                        matched_sec = sec_name
                        break
        if matched_sec:
            current = matched_sec
            continue
        sections[current].append(line)
    return sections


def _parse_projects_from_section(proj_lines: list[str], skills: list[str]) -> list[ProjectHighlight]:
    """Parses all project header styles (pipe-delimited, parenthesized stack, bulleted headers)."""
    projects: list[ProjectHighlight] = []
    current_proj: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current_proj
        if not current_proj:
            return
        name = sanitize_dashes(current_proj["name"]).strip(" .,:;-|")
        summary = sanitize_dashes(" ".join(current_proj["bullets"])).strip()
        techs = current_proj["techs"] or [
            s for s in skills if s.lower() in f"{name} {summary}".lower()
        ][:4]
        if len(name) >= 4:
            projects.append(
                ProjectHighlight(
                    name=name,
                    summary=summary[:260] or name,
                    technologies=techs[:5],
                    scale_or_impact="",
                )
            )
        current_proj = None

    for line in proj_lines:
        if line.lower().startswith("(full ") or line.lower().startswith("references"):
            continue
        is_bullet = line.startswith(("•", "-", "*"))
        clean_bullet = line.lstrip("•-* ").strip()

        # Bullet that starts a project (e.g. "• Enterprise BI & Risk Dashboard (Power BI, DAX): Unified...")
        if is_bullet and ":" in clean_bullet[:85]:
            head, rest = clean_bullet.split(":", 1)
            if len(head) <= 85 and (
                "(" in head or "|" in head or sum(1 for w in head.split() if w[:1].isupper()) >= 2
            ):
                flush()
                techs = _extract_techs_from_header(head, skills)
                clean_title = re.sub(r"\s*\([^)]+\)\s*$", "", head).strip()
                current_proj = {"name": clean_title, "techs": techs, "bullets": [rest.strip()]}
                continue

        if is_bullet:
            if current_proj:
                current_proj["bullets"].append(clean_bullet)
            continue

        # Non-bullet header line (e.g. "VoiceGuard: Real-Time Risk Scoring (voice-guard) | Python, PyTorch")
        if "|" in line or re.search(r"\((?:19|20)\d{2}\)\s*$", line) or (
            len(line) <= 95 and sum(1 for w in line.split()[:4] if w[:1].isupper()) >= 2
        ):
            # Handle wrapped continuation of a header line (e.g., "DAX" on next line)
            if current_proj and not current_proj["bullets"] and len(line) <= 28 and "|" not in line:
                current_proj["techs"] = list(
                    dict.fromkeys(current_proj["techs"] + _extract_techs_from_header(line, skills))
                )
                continue
            flush()
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                title_part = parts[0]
                rest_part = " | ".join(parts[1:])
                techs = _extract_techs_from_header(rest_part, skills)
            else:
                title_part = line
                techs = _extract_techs_from_header(line, skills)
            clean_title = re.sub(r"\s*\((?:20\d{2}|19\d{2})\)\s*$", "", title_part).strip()
            current_proj = {"name": clean_title, "techs": techs, "bullets": []}
        elif current_proj:
            current_proj["bullets"].append(line)

    flush()
    return projects[:6]


def _extract_techs_from_header(header_text: str, known_skills: list[str]) -> list[str]:
    found: list[str] = []
    # Check pipe / comma items directly first
    cleaned = re.sub(r"\b20\d{2}\b", "", header_text)
    for token in re.split(r"[,|/()]+", cleaned):
        t = token.strip()
        if 2 <= len(t) <= 24 and not re.match(r"^(?:present|current)$", t, re.I):
            for sk in KNOWN_TECH_SKILLS:
                if sk.lower() == t.lower() or (len(t) <= 18 and sk.lower() in t.lower()):
                    if sk not in found:
                        found.append(sk)
                    break
            else:
                if len(t.split()) <= 2 and any(ch.isupper() for ch in t) and t not in found:
                    found.append(t)
    if not found:
        lower = header_text.lower()
        found = [s for s in known_skills if s.lower() in lower][:4]
    return found[:5]


def _parse_work_experience(exp_lines: list[str]) -> list[str]:
    roles: list[str] = []
    role_kws = [
        "intern", "developer", "engineer", "consultant", "analyst", "builder",
        "freelance", "manager", "lead", "architect", "technician", "tester", "scientist", "202", "201",
    ]
    for line in exp_lines:
        clean = line.lstrip("•-* ").strip()
        if not clean:
            continue
        is_bullet = line.startswith(("•", "-", "*"))
        if "|" in clean and any(kw in clean.lower() for kw in role_kws):
            roles.append(sanitize_dashes(clean))
        elif not is_bullet and len(clean) <= 90 and any(kw in clean.lower() for kw in role_kws):
            if any(sep in clean for sep in [" - ", " at ", "201", "202", "Present", "Current"]):
                roles.append(sanitize_dashes(clean))
    return roles[:5]


def _parse_certifications(cert_lines: list[str]) -> list[str]:
    certs: list[str] = []
    for line in cert_lines:
        clean = line.lstrip("•-* ").strip()
        if ":" in clean and not clean.lower().startswith("http"):
            clean = clean.split(":", 1)[1].strip()
        for part in re.split(r"\|", clean):
            item = sanitize_dashes(part).strip(" .,")
            if len(item) >= 5 and item not in certs:
                certs.append(item)
    return certs[:8]


KNOWN_CV_TARGET_COMPANIES: list[tuple[str, str]] = [
    ("deloitte infinityx", "Deloitte InfinityX"),
    ("deloitte", "Deloitte"),
    ("amazon data services", "Amazon"),
    ("amazon payments", "Amazon"),
    ("amazon", "Amazon"),
    ("aws", "AWS"),
    ("stripe", "Stripe"),
    ("boxfusion", "Boxfusion"),
    ("bbd", "BBD"),
    ("entelect", "Entelect"),
    ("electrum", "Electrum"),
    ("gendac", "Gendac"),
    ("istore", "iStore (Core Group)"),
    ("core group", "iStore (Core Group)"),
    ("kion group", "KION Group"),
    ("kion", "KION Group"),
    ("dematic", "Dematic (KION)"),
    ("orange cyberdefense", "Orange Cyberdefense"),
    ("sensepost", "Orange Cyberdefense (SensePost)"),
    ("performanta", "Performanta"),
    ("mobius consulting", "Mobius Consulting"),
    ("bluespec holdings", "Bluespec Holdings"),
    ("bluespec", "Bluespec Holdings"),
    ("cape union mart", "Cape Union Mart"),
    ("railway safety regulator", "Railway Safety Regulator (RSR)"),
    ("rsr", "Railway Safety Regulator (RSR)"),
    ("shopritex", "ShopriteX"),
    ("shoprite", "ShopriteX"),
    ("derivco", "Derivco"),
    ("allan gray", "Allan Gray"),
    ("vodacom", "Vodacom"),
    ("mtn", "MTN"),
    ("clickatell", "Clickatell"),
    ("offerzen", "OfferZen"),
    ("takealot", "Takealot"),
    ("discovery", "Discovery"),
    ("capitec", "Capitec"),
    ("standard bank", "Standard Bank"),
    ("investec", "Investec"),
    ("fnb", "FNB"),
    ("nedbank", "Nedbank"),
    ("absa", "Absa"),
    ("luno", "Luno"),
    ("yoco", "Yoco"),
    ("visa", "Visa"),
    ("google", "Google"),
    ("meta", "Meta"),
    ("microsoft", "Microsoft"),
    ("openai", "OpenAI"),
    ("anthropic", "Anthropic"),
    ("crowdstrike", "CrowdStrike"),
    ("palo alto", "Palo Alto Networks"),
]


def detect_opportunity_from_cv_text(
    raw_text: str,
    skills: list[str],
    summary_text: str,
    experience_level: str,
) -> tuple[str, str, str]:
    """
    Universal CV opportunity detector returning:
      (detected_target_company, detected_target_role, seniority_track)
    Inspects the candidate's Summary/Objective/Header for explicit target job mentions first,
    then falls back cleanly to inferring seniority_track and best-fit Target Role from skills & projects.
    """
    normalized = normalize_cv_text(raw_text)
    target_scope = summary_text.strip() or normalized[:900]
    head_lower = target_scope.lower()
    full_lower = normalized.lower()

    # 1. Seniority track ("vac_work" | "intern_grad" | "junior" | "mid_senior")
    if any(k in head_lower or k in full_lower[:900] for k in ["vac work", "vacation work", "holiday work", "winter school", "summer school", "vac programme"]):
        seniority_track = "vac_work"
    elif any(k in head_lower for k in ["intern", "internship", "graduate programme", "grad programme", "graduate trainee", "bursary", "final-year", "final year", "student", "learnership", "expected graduation"]):
        seniority_track = "intern_grad"
    elif any(k in experience_level.lower() for k in ["senior", "staff", "principal", "lead", "mid-level"]):
        seniority_track = "mid_senior"
    else:
        seniority_track = "junior"

    detected_company = ""
    detected_role = ""

    # 2. Match explicit target company mentioned in Summary / Objective right next to employer context cues
    # Mask out software product phrases ("Microsoft Excel", "Google Gemini", "Oracle Retail", "AWS Concepts")
    masked_head = re.sub(
        r"\bmicrosoft\s+(?:excel|word|powerpoint|power\s+bi|office|sql|azure|teams|365)\b|\bgoogle\s+(?:gemini|cloud|analytics|workspace|chrome|colab)\b|\boracle\s+(?:retail|analytics|database|sql|cloud)\b",
        " ",
        head_lower,
    )
    for pattern, canonical in KNOWN_CV_TARGET_COMPANIES:
        esc = re.escape(pattern)
        # Require explicit target/employer phrasing right adjacent to the company name
        anchor_pre = rf"\b(?:at|with|within|through|to|join(?:ing)?|applying\s+for)\s+(?:the\s+)?{esc}(?![a-z0-9])"
        anchor_post = rf"(?<![a-z0-9]){esc}(?:'s|’s)?\s+(?:software|graduate|grad|intern|internship|vac|bursary|retail|payments|programme|role)\b"
        anchor_comma = rf"(?:intern|graduate|engineer|developer|analyst|manager),\s*{esc}(?![a-z0-9])"
        if re.search(anchor_pre, masked_head) or re.search(anchor_post, masked_head) or re.search(anchor_comma, masked_head):
            detected_company = canonical
            break

    # Special signature for Visa VCA / Product summary without explicit word "Visa"
    if not detected_company and ("vca internship" in head_lower or "visa consulting" in head_lower):
        detected_company = "Visa"
    elif not detected_company and "customer value proposition (cvp)" in head_lower and "product internship" in head_lower:
        detected_company = "Visa"

    # Generic pattern capture for unlisted target companies in Summary ("role at Acme Corp", "as a ... Intern at Acme")
    if not detected_company:
        m_comp = re.search(
            r"(?:role at|position at|intern(?:ship)?(?:,|\s+role)?\s+at|graduate\s+at|join(?:ing)?\s+(?:the\s+)?|seeking\s+(?:a|an|the)\s+[^.\n]{3,45}\s+at)\s+([A-Z][A-Za-z0-9&.\- ]{2,42}?)(?=\s+(?:in|to|as|where|building|and|on)\b|[.,;()\n]|$)",
            target_scope,
        )
        if m_comp:
            cand = m_comp.group(1).strip(" .,")
            if cand.lower() not in {"eduvos", "quarphix", "hexsoftwares", "sci-bono"} and len(cand) >= 2:
                detected_company = cand

    # Refine Deloitte -> Deloitte InfinityX if InfinityX appears
    if detected_company == "Deloitte" and "infinityx" in head_lower:
        detected_company = "Deloitte InfinityX"

    # 3. Extract explicit target role from Summary / Objective
    role_phrases = [
        (r"data\s+analyst\s*,?\s*intern", "Data Analyst Intern"),
        (r"\bbi\s+intern\b|business\s+intelligence\s+intern", "Business Intelligence (BI) Intern"),
        (r"data\s+center\s+operations\s*\(?(?:dco)?\)?\s*tech\s+intern", "Data Center Operations (DCO) Tech Intern"),
        (r"software\s+development\s+engineer\s+intern", "Software Development Engineer Intern"),
        (r"program\s*/?\s*product\s+manager\s+intern|product\s+management\s+intern|product\s+internship", "Product Management Intern"),
        (r"business\s+developer\s+intern", "Business Developer Intern"),
        (r"ai\s+developer\s+intern", "AI Developer Intern"),
        (r"vca\s+intern(?:ship)?|visa\s+consulting", "Visa Consulting & Analytics (VCA) Intern"),
        (r"technology\s*&\s*transformation|consulting\s+career.*infinityx|infinityx\s+graduate", "Technology Consulting Graduate (InfinityX)"),
        (r"bursary\s+programme", "Software Engineering & Data Analytics Bursary"),
        (r"software\s+engineering\s+grad(?:uate)?\s+programme", "Graduate Software Engineer"),
        (r"vac(?:ation)?\s*work|holiday\s+work", "Vacation Work (Vac Work) Student"),
        (r"cyber\s*security\s+analyst|soc\s+analyst|penetration\s+tester|pentester", "Cybersecurity Analyst / Penetration Tester"),
        (r"(?:technical\s+)?project\s+manager|scrum\s+master|delivery\s+manager", "Technical Project Manager"),
        (r"product\s+manager", "Product Manager"),
        (r"business\s+analyst", "Technical Business Analyst"),
        (r"qa\s+(?:automation\s+)?engineer|sdet|quality\s+assurance", "QA Automation / SDET Engineer"),
    ]
    for pat, label in role_phrases:
        if re.search(pat, head_lower):
            detected_role = label
            break

    # Generic fallback role extraction ("as a <Role Title> at" or "seeking the <Role Title> role")
    if not detected_role:
        m_role = re.search(
            r"(?:as\s+a(?:n)?\s+(?:202\d\s+)?|seeking\s+(?:the|a|an)\s+)([A-Z][A-Za-z0-9/()\-& ]{4,55}?)(?=\s+(?:role\s+)?(?:at|with|within|in)\b|[.,;\n])",
            head_scope,
        )
        if m_role:
            candidate_r = sanitize_dashes(m_role.group(1)).strip(" ,")
            if 4 <= len(candidate_r) <= 58:
                detected_role = candidate_r

    # 4. If still no explicit role, infer best-fit role purely from the candidate's dominant CV skills & projects
    if not detected_role:
        skills_low = " ".join(skills).lower() + " " + full_lower[:2000]
        if any(k in skills_low for k in ["pentest", "penetration testing", "owasp", "siem", "soc analyst", "burp suite", "metasploit"]):
            detected_role = "Cybersecurity Analyst / Penetration Tester"
        elif any(k in skills_low for k in ["critical path", "wbs", "projectlibre", "scrum master", "sprint planning", "agile delivery"]):
            detected_role = "Technical Project Manager"
        elif any(k in skills_low for k in ["product roadmap", "prd", "customer value proposition", "usability engineering", "product management"]):
            detected_role = "Product Manager Intern" if seniority_track in {"vac_work", "intern_grad"} else "Product Manager"
        elif any(k in skills_low for k in ["power bi", "dax", "power query", "star schema", "tableau"]):
            detected_role = "Business Intelligence (BI) Intern" if seniority_track in {"vac_work", "intern_grad"} else "Data / BI Analyst"
        elif any(k in skills_low for k in ["pytorch", "onnx", "rag", "llm", "machine learning", "generative ai"]):
            detected_role = "AI Developer Intern" if seniority_track in {"vac_work", "intern_grad"} else "Machine Learning / AI Engineer"
        elif any(k in skills_low for k in ["hardware diagnostics", "linux", "tcp/ip", "server", "rack", "data center"]):
            detected_role = "Data Center Operations (DCO) Tech Intern" if seniority_track in {"vac_work", "intern_grad"} else "IT Systems / Cloud Operations Engineer"
        elif seniority_track == "vac_work":
            detected_role = "Vacation Work (Vac Work) Student"
        elif seniority_track == "intern_grad":
            detected_role = "Graduate Software Engineer"
        elif any(k in skills_low for k in ["react", "next.js", "tailwind"]) and any(k in skills_low for k in ["fastapi", "django", "node", "sql"]):
            detected_role = "Full-Stack Engineer"
        else:
            detected_role = "Backend Engineer"

    return detected_company, detected_role, seniority_track


def extract_profile_heuristic(raw_text: str) -> CandidateProfile:
    """ATS-grade deterministic parser handling all CV formats: student, vac-work, grad, consulting, SWE, PM, Cybersec."""
    normalized = normalize_cv_text(raw_text)
    sections = _segment_ats_sections(normalized)

    # 1. Name & Location
    header_lines = sections["HEADER"] or [ln.strip() for ln in normalized.splitlines() if ln.strip()][:5]
    candidate_name = "Candidate Profile"
    for hline in header_lines[:3]:
        clean_h = hline.strip()
        if 2 <= len(clean_h.split()) <= 4 and len(clean_h) <= 45 and not any(ch in clean_h for ch in "@:/|0123456789"):
            candidate_name = clean_h.title() if clean_h.isupper() else clean_h
            break

    header_blob = " ".join(header_lines)
    location = "South Africa"
    for loc_pat in [
        r"(Midrand,\s*Gauteng)",
        r"(Pretoria,\s*Gauteng)",
        r"(Centurion,\s*Gauteng)",
        r"(Sandton,\s*Gauteng)",
        r"(Cape Town,\s*Western Cape)",
        r"(Stellenbosch,\s*Western Cape)",
        r"(Durban,\s*KwaZulu-?Natal)",
        r"(Johannesburg,\s*South Africa)",
        r"(Johannesburg Metropolitan Area)",
        r"(Midrand\s+Gauteng)",
        r"(San Francisco,\s*CA)",
        r"(New York,\s*NY)",
        r"(Austin,\s*TX)",
        r"(Seattle,\s*WA)",
        r"(London,\s*UK)",
        r"(Berlin,\s*Germany)",
    ]:
        m = re.search(loc_pat, header_blob, flags=re.I)
        if m:
            location = m.group(1).replace("Midrand Gauteng", "Midrand, Gauteng")
            break
    if location == "South Africa":
        generic_loc = re.search(r"\b([A-Z][a-z]{2,18},\s*[A-Z][A-Za-z ]{1,20})\b", header_blob)
        if generic_loc:
            location = generic_loc.group(1).strip()

    # 2. Academic Standing / Experience Level
    lower = normalized.lower()
    avg_match = re.search(r"(\d{2}(?:\.\d)?%)\s*(?:academic\s+)?average", lower)
    dist_match = re.search(r"(\d+)\s+distinctions?", lower)
    years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", lower)

    is_student_or_grad = any(
        kw in lower for kw in ["bsc", "bcom", "beng", "student", "expected graduation", "graduate", "intern", "learnership", "vac work", "vacation work"]
    )
    if avg_match and dist_match:
        years_badge = f"{avg_match.group(1)} avg · {dist_match.group(1)} distinctions"
    elif avg_match:
        years_badge = f"{avg_match.group(1)} academic avg"
    elif "top 3 achiever" in lower:
        years_badge = "Top 3 Achiever · BSc IT"
    elif years_match:
        y = int(years_match.group(1))
        years_badge = "1 year experience" if y == 1 else f"{y} years experience"
    else:
        years_badge = "Hands-on experience & projects"

    if "staff" in lower or "principal" in lower:
        level = "Staff / Principal engineer"
    elif "senior" in lower and not is_student_or_grad:
        level = "Senior engineer"
    elif "final-year" in lower or ("expected graduation" in lower and "2026" in lower):
        level = "Final-year BSc IT (SWE)"
    elif is_student_or_grad:
        level = "BSc IT (SWE) · Grad / Intern"
    elif years_match and int(years_match.group(1)) >= 3:
        level = "Mid-level engineer"
    else:
        level = "Software & Tech Builder"

    # 3. Education line
    edu_lines = sections["EDUCATION"]
    education = ""
    for el in edu_lines:
        if any(k in el.lower() for k in ["bsc", "bcom", "beng", "bachelor", "master", "honours", "university", "eduvos", "degree", "diploma"]):
            education = sanitize_dashes(el.split("|")[0].strip())
            break

    # 4. Skills (prioritize SKILLS section hits, then whole CV)
    skills_blob = " ".join(sections["SKILLS"]).lower() or lower
    skills: list[str] = []
    for sk in KNOWN_TECH_SKILLS:
        pat = rf"(?<![A-Za-z0-9]){re.escape(sk.lower())}(?![A-Za-z0-9])"
        if re.search(pat, skills_blob) or re.search(pat, lower):
            if sk not in skills:
                skills.append(sk)
    skills = skills[:10] or ["Python", "SQL", "TypeScript", "React"]

    # 5. Projects, Experience, Certifications
    projects = _parse_projects_from_section(sections["PROJECTS"], skills)
    if not projects:
        verb_matches = re.findall(
            r"(?:Architected|Built|Designed|Engineered|Developed|Led)\s+(?:a|an|the)?\s*([A-Z][A-Za-z0-9\-/& ]{4,42}?)(?=\s+(?:ingesting|processing|handling|in|using|for|with|that|to|across)\b|[.,;\n]|$)",
            normalized,
        )
        for vm in verb_matches[:4]:
            projects.append(ProjectHighlight(name=vm.strip(), summary=vm.strip(), technologies=skills[:3]))

    work_experience = _parse_work_experience(sections["EXPERIENCE"])
    certifications = _parse_certifications(sections["CERTIFICATIONS"])

    # 6. Opportunity detection (Target Company, Target Role & Seniority Track)
    summary_text = " ".join(sections["SUMMARY"])
    detected_company, detected_role, seniority_track = detect_opportunity_from_cv_text(
        raw_text=normalized,
        skills=skills,
        summary_text=summary_text,
        experience_level=level,
    )

    if projects:
        lead_name = projects[0].name.split(":")[0].split("(")[0].strip()
        summary_line = (
            f"Extracted {len(projects)} projects (including {lead_name}), "
            f"{len(work_experience)} experience roles, and {len(skills)} core skills."
            if work_experience
            else f"Found {len(projects)} projects, including {lead_name}."
        )
    elif work_experience:
        summary_line = f"Extracted {len(work_experience)} experience roles and {len(skills)} core skills."
    else:
        summary_line = f"Extracted core experience across {', '.join(skills[:4])}."

    return CandidateProfile(
        candidate_name=candidate_name,
        experience_level=level,
        years_experience=years_badge,
        location=location,
        primary_skills=skills,
        projects=projects,
        work_experience=work_experience,
        certifications=certifications,
        education=education,
        extraction_method="Text extracted",
        projects_summary_line=summary_line,
        detected_target_company=detected_company,
        detected_target_role=detected_role,
        seniority_track=seniority_track,
    )


async def extract_profile_with_computer_vision(
    raw_text: str,
    page_images_b64: list[str],
    heuristic_profile: CandidateProfile,
) -> CandidateProfile:
    """
    Multimodal Computer Vision + ATS CV reader powered by Gemini Vision.
    Reads rendered page screenshots (visual columns, bold titles, tables, percentages)
    alongside extracted text so complex or scanned CVs parse with high fidelity.
    """
    if not settings.gemini_api_key:
        return heuristic_profile

    prompt_text = f"""You are an enterprise ATS + Computer Vision CV reader.
Inspect the attached CV page images (if provided) AND the extracted text below to produce an exact, structured candidate profile.
Rules:
1. Extract ONLY facts visible on the CV. Never invent skills, jobs, or projects.
2. Never use em dashes or en dashes. Use standard hyphens (-) or middots cleanly.
3. Capture ALL distinct projects with their exact project title, concise 1-sentence technical summary, and technologies.
4. For students/graduates with academic averages/distinctions, set "years_experience" to a crisp badge like "82.4% avg · 14 distinctions" (or "N years experience" for experienced professionals).
5. Look at the CV's Professional Summary / Objective / Header to detect if the candidate is applying for a specific company and/or target role (e.g. "BBD Software Engineering Grad Programme" -> detected_target_company: "BBD", detected_target_role: "Graduate Software Engineer"; "Data Analyst, Intern at Stripe" -> detected_target_company: "Stripe", detected_target_role: "Data Analyst Intern"). If NO specific company is mentioned in the summary/objective, leave "detected_target_company" as "" and set "detected_target_role" to the role best supported by the candidate's CV.
6. Set "seniority_track" strictly to one of: "vac_work", "intern_grad", "junior", "mid_senior".
7. Return STRICT JSON matching these keys:
{{
  "candidate_name": "...",
  "experience_level": "short crisp badge (e.g. 'Final-year BSc IT (SWE)' or 'Mid-level engineer')",
  "years_experience": "short crisp badge (e.g. '82.4% avg · 14 distinctions' or '4 years experience')",
  "location": "City, Country/Province",
  "education": "Degree and institution",
  "primary_skills": ["up to 10 core technical/domain skills"],
  "projects": [
    {{"name": "Exact Project Title", "summary": "1 concise sentence", "technologies": ["Tech1", "Tech2"], "scale_or_impact": "metric if any"}}
  ],
  "work_experience": ["Role Title at Company (Dates)"],
  "certifications": ["Certification Name"],
  "projects_summary_line": "1 crisp summary sentence naming the project count and top project.",
  "detected_target_company": "Target company name if explicitly stated in CV objective/summary, else empty string",
  "detected_target_role": "Target role stated in CV or inferred best-matching tech role",
  "seniority_track": "vac_work | intern_grad | junior | mid_senior"
}}

EXTRACTED TEXT:
{raw_text[:9000]}
"""

    parts: list[dict[str, Any]] = [{"text": prompt_text}]
    for img_b64 in page_images_b64[:4]:
        parts.append({"inlineData": {"mimeType": "image/png", "data": img_b64}})

    candidate_models = [settings.gemini_model, "gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview"]
    seen_models: list[str] = []
    for m in candidate_models:
        if m and m not in seen_models:
            seen_models.append(m)

    for model_name in seen_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
            }
            async with httpx.AsyncClient(timeout=28.0) as client:
                r = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
                if r.status_code >= 400:
                    continue
                data = r.json()
            raw_json = "".join(
                p.get("text", "")
                for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            ).strip()
            if raw_json.startswith("```"):
                raw_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_json)
            parsed = json.loads(raw_json)
            parsed["extraction_method"] = "Text extracted"
            if not parsed.get("projects") and heuristic_profile.projects:
                parsed["projects"] = [p.model_dump() for p in heuristic_profile.projects]
            if not parsed.get("work_experience") and heuristic_profile.work_experience:
                parsed["work_experience"] = heuristic_profile.work_experience
            vision_comp = (parsed.get("detected_target_company") or "").strip()
            if vision_comp and not raw_text.startswith("[Image CV"):
                comp_tok = vision_comp.lower().split()[0]
                if len(comp_tok) >= 3 and comp_tok not in raw_text.lower() and not (comp_tok == "visa" and "vca" in raw_text.lower()):
                    parsed["detected_target_company"] = heuristic_profile.detected_target_company
            if not parsed.get("detected_target_company") and heuristic_profile.detected_target_company:
                parsed["detected_target_company"] = heuristic_profile.detected_target_company
            if not parsed.get("detected_target_role") and heuristic_profile.detected_target_role:
                parsed["detected_target_role"] = heuristic_profile.detected_target_role
            if parsed.get("seniority_track") not in {"vac_work", "intern_grad", "junior", "mid_senior"}:
                parsed["seniority_track"] = heuristic_profile.seniority_track
            profile = CandidateProfile(**parsed)
            profile.candidate_name = sanitize_dashes(profile.candidate_name)
            profile.experience_level = sanitize_dashes(profile.experience_level)
            profile.years_experience = sanitize_dashes(profile.years_experience)
            profile.projects_summary_line = sanitize_dashes(profile.projects_summary_line)
            profile.detected_target_company = sanitize_dashes(profile.detected_target_company)
            profile.detected_target_role = sanitize_dashes(profile.detected_target_role)
            return profile
        except Exception as exc:
            logger.debug("CV Vision extraction via %s skipped: %s", model_name, exc)

    return heuristic_profile


def extract_jd_signals(job_description: str, target_role: str = "") -> list[str]:
    lower = f"{target_role} {job_description}".lower()
    signal_map = [
        ("SQL & data modeling", ["sql", "postgresql", "star schema", "dax", "warehouse", "semantic layer"]),
        ("API & backend design", ["api", "rest", "graphql", "endpoint", "flask", "fastapi", "microservices"]),
        ("Distributed systems", ["distributed", "scale", "queue", "kafka", "consistency", "latency"]),
        ("AI & LLM pipelines", ["llm", "ai", "pytorch", "onnx", "validation", "rag", "machine learning"]),
        ("BI & analytics", ["power bi", "dashboard", "analytics", "metrics", "excel", "oracle retail"]),
        ("Case & client consulting", ["consulting", "stakeholder", "business case", "transformation", "vca", "client"]),
        ("Data center & Linux ops", ["data center", "dco", "hardware", "linux", "tcp/ip", "sla", "server"]),
        ("OOP & clean architecture", ["oop", "java", "c#", ".net", "shesha", "design patterns", "testing"]),
        ("Security & threat triage", ["owasp", "siem", "pentest", "vulnerability", "zero trust", "popia", "soc"]),
        ("Product & project delivery", ["roadmap", "prd", "scrum", "wbs", "critical path", "sprint", "stakeholder"]),
        ("Industrial & automation", ["plc", "intralogistics", "wms", "wcs", "embedded", "robotics", "kion"]),
        ("Ownership", ["ownership", "end-to-end", "autonomous", "bias for action", "lead"]),
        ("Frontend architecture", ["react", "next.js", "typescript", "browser", "ui"]),
    ]
    found: list[str] = []
    for label, kws in signal_map:
        if any(k in lower for k in kws):
            found.append(label)
        if len(found) >= 4:
            break
    if not found:
        found = ["Technical depth", "System design", "Ownership"]
    return found
