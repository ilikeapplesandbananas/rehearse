import rawIntelDb from "@/data/company_intelligence.json";
import type {
  ArchetypeOverview,
  CVDocument,
  CandidateProfile,
  CompanyResearchResult,
  DeliveryMetrics,
  EngineSettingsStatus,
  EvaluationResult,
  ExplorePillar,
  InterviewSession,
  KnownCompanyItem,
  OverviewStats,
  QuestionAttempt,
  SessionQuestion,
  StudyMaterialItem,
  StudyPlanRecord,
} from "@/types/rehearse";

interface RawRoleInfo {
  label: string;
  keywords: string[];
  round_weights?: string[];
  core_topics: string[];
  role_grading_focus?: string[];
  jd_responsibilities?: string;
  jd_requirements?: string;
}

interface RawArchetype {
  id: string;
  name: string;
  short_label: string;
  summary: string;
  shared_companies: string[];
  standard_rounds: { stage: string; name: string; duration: string; format: string }[];
  intern_grad_rounds?: { stage: string; name: string; duration: string; format: string }[];
  evaluation_bar: string[];
  company_grading_rubric?: string[];
  expected_answer_structure?: string;
  coding_and_leetcode_patterns?: string[];
  signature_questions?: {
    category: string;
    short_title: string;
    question: string;
    guidance: string[];
  }[];
}

interface RawOverride {
  display_name: string;
  archetype_id: string;
  domain_context?: string;
  nuances?: string[];
  company_grading_rubric?: string[];
  expected_answer_structure?: string;
  coding_and_leetcode_patterns?: string[];
}

const DB = rawIntelDb as unknown as {
  meta: { sources: string[] };
  archetypes: Record<string, RawArchetype>;
  company_overrides: Record<string, RawOverride>;
  roles: Record<string, RawRoleInfo>;
};

const STORAGE_SESSIONS = "rehearse_static_sessions_v1";
const STORAGE_STUDY = "rehearse_static_study_v1";
const STORAGE_GEMINI_KEY = "rehearse_browser_gemini_key_v1";

function safeStorageGet<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function safeStorageSet<T>(key: string, value: T): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore storage quota failures
  }
}

function makeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function cleanDashes(text: string): string {
  return text
    .replace(/\u2014/g, ", ")
    .replace(/\u2013/g, "-")
    .replace(/\ufffd/g, "-")
    .replace(/\s+,\s+/g, ", ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function smartTrim(text: string, maxLen: number): string {
  const clean = cleanDashes(text);
  if (clean.length <= maxLen) return clean.replace(/[ .,:;/(]+$/, "");
  let cut = clean.slice(0, maxLen).replace(/\s+\S*$/, "").trim();
  if ((cut.match(/\(/g) || []).length > (cut.match(/\)/g) || []).length) {
    cut = cut.slice(0, cut.lastIndexOf("(")).trim();
  }
  return cut.replace(/[ .,:;/(-]+$/, "");
}

function normalizeCompanyKey(companyName: string): string {
  return companyName
    .toLowerCase()
    .replace(/[^a-z0-9\s]+/g, "")
    .replace(/\s+(inc|llc|ltd|pty|corp|corporation|technologies|tech|labs|group|co|sa|international)$/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function detectRoleKey(targetRole: string, jd = ""): string {
  const roleLow = targetRole.toLowerCase();
  const jdLow = jd.slice(0, 500).toLowerCase();
  let bestKey = "backend";
  let bestScore = 0;
  for (const [rKey, rInfo] of Object.entries(DB.roles)) {
    let score = 0;
    for (const kw of rInfo.keywords || []) {
      if (roleLow.includes(kw)) score = Math.max(score, 100 + kw.length);
      else if (jdLow.includes(kw)) score = Math.max(score, 20 + kw.length);
    }
    if (score > bestScore) {
      bestScore = score;
      bestKey = rKey;
    }
  }
  return bestKey;
}

function detectSeniorityTrack(targetRole: string, expLevel = "", jd = ""): string {
  const r = targetRole.toLowerCase();
  const e = expLevel.toLowerCase();
  const j = jd.slice(0, 400).toLowerCase();
  if (/(vac work|vacation work|holiday work|winter school|summer school|vac student)/.test(r)) {
    return "vac_work";
  }
  if (/(senior|staff|principal|lead|head of|architect)/.test(r)) {
    return "mid_senior";
  }
  if (/(intern|graduate|grad |bursary|trainee|junior|entry)/.test(r)) {
    return "intern_grad";
  }
  if (/(vac work|vacation work)/.test(e) || /(vacation work|vac work)/.test(j)) {
    return "vac_work";
  }
  if (/(student|final-year|grad|intern|learnership)/.test(e) || /(internship|graduate programme|grad programme)/.test(j)) {
    return "intern_grad";
  }
  return "junior";
}

function findCuratedMatch(companyName: string): { archId: string; override: RawOverride | null } {
  const key = normalizeCompanyKey(companyName);
  const rawLow = companyName.toLowerCase().trim();
  if (DB.company_overrides[key]) {
    const ov = DB.company_overrides[key];
    return { archId: ov.archetype_id, override: ov };
  }
  if (DB.company_overrides[rawLow]) {
    const ov = DB.company_overrides[rawLow];
    return { archId: ov.archetype_id, override: ov };
  }
  const sorted = Object.entries(DB.company_overrides).sort((a, b) => b[0].length - a[0].length);
  for (const [ovKey, ov] of sorted) {
    if (ovKey.length <= 4) {
      if (new RegExp(`\\b${ovKey}\\b`).test(key) || new RegExp(`\\b${ovKey}\\b`).test(rawLow)) {
        return { archId: ov.archetype_id, override: ov };
      }
    } else if (key.includes(ovKey) || ovKey.includes(key) || rawLow.includes(ovKey)) {
      return { archId: ov.archetype_id, override: ov };
    }
  }
  for (const [archId, arch] of Object.entries(DB.archetypes)) {
    for (const shared of arch.shared_companies) {
      const sKey = normalizeCompanyKey(shared);
      if (sKey === key || (key.length >= 4 && sKey.length >= 4 && (sKey.includes(key) || key.includes(sKey)))) {
        return {
          archId,
          override: {
            display_name: shared,
            archetype_id: archId,
            nuances: [`Shares the '${arch.name}' format used across ${arch.shared_companies.slice(0, 4).join(", ")}.`],
          },
        };
      }
    }
  }
  return { archId: "sa_software_grad_consultancy", override: null };
}

export function staticFetchArchetypes(): {
  archetypes: ArchetypeOverview[];
  companies: KnownCompanyItem[];
} {
  const seen = new Set<string>();
  const companies: KnownCompanyItem[] = [];
  for (const ov of Object.values(DB.company_overrides)) {
    const arch = DB.archetypes[ov.archetype_id];
    const k = normalizeCompanyKey(ov.display_name);
    if (!seen.has(k) && arch) {
      seen.add(k);
      companies.push({ name: ov.display_name, archetype_id: arch.id, archetype_label: arch.short_label });
    }
  }
  for (const arch of Object.values(DB.archetypes)) {
    for (const name of arch.shared_companies) {
      const k = normalizeCompanyKey(name);
      if (!seen.has(k)) {
        seen.add(k);
        companies.push({ name, archetype_id: arch.id, archetype_label: arch.short_label });
      }
    }
  }
  companies.sort((a, b) => a.name.localeCompare(b.name));
  return { archetypes: Object.values(DB.archetypes), companies };
}

export function staticResearchCompany(
  company_name: string,
  target_role: string,
  job_description = "",
  experience_level = ""
): CompanyResearchResult {
  const { archId, override } = findCuratedMatch(company_name);
  const arch = DB.archetypes[archId] || DB.archetypes.pragmatic_fintech_api;
  const display = cleanDashes(override?.display_name || company_name.trim() || "Tech Company");
  const roleKey = detectRoleKey(target_role, job_description);
  const roleInfo = DB.roles[roleKey] || DB.roles.backend;
  const roleLabel = cleanDashes(target_role.trim() || roleInfo.label);
  const seniorityTrack = detectSeniorityTrack(roleLabel, experience_level, job_description);

  const rounds =
    seniorityTrack === "vac_work" || seniorityTrack === "intern_grad"
      ? arch.intern_grad_rounds || arch.standard_rounds
      : arch.standard_rounds;

  const rubric = Array.from(
    new Set([...(override?.company_grading_rubric || []), ...(arch.company_grading_rubric || [])].map(cleanDashes))
  ).slice(0, 5);
  const expectedStruct = cleanDashes(
    override?.expected_answer_structure ||
      arch.expected_answer_structure ||
      "Context -> Core execution -> Edge cases & trade-offs -> Quantified impact"
  );
  const codingPatterns = Array.from(
    new Set([...(override?.coding_and_leetcode_patterns || []), ...(arch.coding_and_leetcode_patterns || [])].map(cleanDashes))
  ).slice(0, 5);

  const domainContext = cleanDashes(override?.domain_context || `engineering and technology systems in ${arch.short_label}`);
  const levelIntro =
    seniorityTrack === "vac_work"
      ? `Join ${display}'s structured Vacation Work (Vac Work) programme inside our ${domainContext}. Work alongside senior engineers and mentors on real sprint deliverables.`
      : seniorityTrack === "intern_grad"
      ? `Join ${display} as a ${roleLabel} working across ${domainContext}. Contribute to production deliverables while growing through structured feedback and reviews.`
      : `Join ${display} as a ${roleLabel} driving core initiatives across ${domainContext}.`;

  const resp = roleInfo.jd_responsibilities || "Design, build, and verify reliable engineering and data solutions.";
  const req = roleInfo.jd_requirements || "Strong CS, SQL/data, and problem-solving fundamentals.";
  const researchedJd = cleanDashes(
    `${levelIntro}\n\nKey Responsibilities: ${resp}\n\nRequirements & ${display} Evaluation Bar: ${req} Interviewers evaluate specifically for: ${
      rubric[0] || "Clear structured reasoning and ownership"
    }.`
  );

  const shortRole = roleLabel.split("(")[0].trim().slice(0, 32);
  const topTopic = roleInfo.core_topics[0] || "Core technical execution";
  const isCoding = /software|swe|engineer|dev|vac|grad|dematic|kion|gendac|electrum|cyber|bbd/.test(
    `${roleLabel.toLowerCase()} ${arch.id}`
  );
  const p2Desc =
    codingPatterns[0] && isCoding
      ? cleanDashes(`${topTopic.split(":")[0]}. Coding focus: ${smartTrim(codingPatterns[0], 78)}.`)
      : cleanDashes(`${smartTrim(topTopic, 86)}.`);

  const pillars: ExplorePillar[] = [
    {
      index: "01",
      title: seniorityTrack === "vac_work" ? "CV projects & curiosity" : seniorityTrack === "intern_grad" ? "Projects & problem solving" : "Architecture & ownership",
      description:
        seniorityTrack === "vac_work"
          ? `Thinking out loud on your university/GitHub projects and rapid learning at ${display}.`
          : `Deep probing on your CV projects and how you reason under ${display} standards.`,
    },
    { index: "02", title: cleanDashes(`${shortRole} core`), description: p2Desc },
    {
      index: "03",
      title: cleanDashes(`How ${display} marks answers`),
      description: cleanDashes(`${arch.short_label} rubric: ${smartTrim(expectedStruct, 105)}.`),
    },
  ];

  const peers = arch.shared_companies.filter((c) => normalizeCompanyKey(c) !== normalizeCompanyKey(display));
  return {
    company_name: display,
    normalized_key: normalizeCompanyKey(display),
    archetype_id: arch.id,
    archetype_name: cleanDashes(arch.name),
    archetype_short_label: cleanDashes(arch.short_label),
    shared_companies: peers.slice(0, 6),
    deduplication_note: cleanDashes(
      `Matches the ${arch.short_label} blueprint shared with ${peers.slice(0, 4).join(", ")}, calibrated for ${display}'s ${roleLabel} bar.`
    ),
    summary: cleanDashes(arch.summary),
    rounds,
    company_nuances: (override?.nuances || []).map(cleanDashes),
    evaluation_bar: arch.evaluation_bar.map(cleanDashes),
    role_key: roleKey,
    role_label: roleLabel,
    role_core_topics: roleInfo.core_topics.map(cleanDashes),
    seniority_track: seniorityTrack,
    researched_job_description: researchedJd,
    explore_pillars: pillars,
    company_grading_rubric: rubric,
    expected_answer_structure: expectedStruct,
    coding_and_leetcode_patterns: codingPatterns,
    role_grading_focus: (roleInfo.role_grading_focus || []).map(cleanDashes),
    researched_live: false,
    sources: DB.meta.sources.slice(0, 4),
  };
}

const SAMPLE_CV_TEXT = `MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Johannesburg, South Africa | South African Citizen

PROFESSIONAL SUMMARY
Analytical, ambitious builder pursuing a quantitative BSc in Information Technology: Software Engineering (82.4% average across 19 passed modules, 14 distinctions | Expected Graduation: December 2027). Experienced in SQL (93% Distinction - 100% Final Exam), Python (91% Distinction), building scalable data pipelines, designing metrics semantic layers and executive dashboards (Microsoft Power BI, React/Recharts), and leveraging AI tools cleanly. Ready to own high-impact analytics deliverables end to end as a Data Analyst, Intern at Stripe.`;

function parseProfileFromText(rawText: string): CandidateProfile {
  const lower = rawText.toLowerCase();
  const lines = rawText.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const firstLine = lines.find((l) => l.split(/\s+/).length >= 2 && l.split(/\s+/).length <= 4 && !/[@:/|0-9]/.test(l));
  const candidate_name = firstLine
    ? firstLine === firstLine.toUpperCase()
      ? firstLine.replace(/\w\S*/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase())
      : firstLine
    : "Mbesa Lephoto";

  const skillsList = ["Python", "SQL", "TypeScript", "Java", "C#", ".NET", "React", "Next.js", "FastAPI", "Power BI", "DAX", "PyTorch", "Docker", "AWS", "Linux", "OWASP", "SIEM"];
  const primary_skills = skillsList.filter((sk) => lower.includes(sk.toLowerCase())).slice(0, 8);
  if (primary_skills.length === 0) primary_skills.push("Python", "SQL", "TypeScript");

  const projects: { name: string; summary: string; technologies: string[]; scale_or_impact: string }[] = [];
  for (const ln of lines) {
    if (ln.includes("|") && !ln.startsWith("072") && !ln.includes("@") && ln.length < 110) {
      const [name, rest] = ln.split("|", 2);
      const cleanName = name.trim();
      if (cleanName.length >= 4 && !/summary|education|skills|experience|projects|certifications|eduvos|quarphix|hexsoftwares/i.test(cleanName)) {
        projects.push({
          name: cleanName,
          summary: `${cleanName} (${rest.trim()})`,
          technologies: primary_skills.slice(0, 3),
          scale_or_impact: "",
        });
      }
    }
  }
  if (projects.length === 0) {
    projects.push(
      {
        name: "Enterprise Metrics Semantic Layer",
        summary: "Unified five operational datasets in Power BI with a Star Schema and reusable DAX KPIs.",
        technologies: ["Power BI", "DAX", "SQL"],
        scale_or_impact: "Flagged 771 critical stockouts",
      },
      {
        name: "Lightning Webstore",
        summary: "Fault-tolerant payment processing web application with strict SQL transaction checks.",
        technologies: ["Python", "Flask", "SQL"],
        scale_or_impact: "",
      }
    );
  }

  let detected_target_company = "";
  const masked = lower.replace(/\bmicrosoft\s+(?:excel|word|powerpoint|power\s+bi|sql|azure)\b/g, " ");
  for (const [ovKey, ov] of Object.entries(DB.company_overrides)) {
    const escaped = ovKey.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pre = new RegExp(`\\b(?:at|with|within|through|to|join(?:ing)?|applying\\s+for)\\s+(?:the\\s+)?${escaped}\\b`);
    const post = new RegExp(`\\b${escaped}(?:'s|s)?\\s+(?:software|graduate|grad|intern|internship|vac|bursary|programme)`);
    if (pre.test(masked) || post.test(masked)) {
      detected_target_company = ov.display_name;
      break;
    }
  }

  let detected_target_role = "";
  if (/data analyst/.test(lower)) detected_target_role = "Data Analyst Intern";
  else if (/vac work|vacation work/.test(lower)) detected_target_role = "Vacation Work (Vac Work) Student";
  else if (/grad(?:uate)? programme|software engineering grad/.test(lower)) detected_target_role = "Graduate Software Engineer";
  else if (/cyber|pentest|soc analyst/.test(lower)) detected_target_role = "Cybersecurity Analyst / Penetration Tester";
  else if (/project manager|scrum master/.test(lower)) detected_target_role = "Technical Project Manager";
  else if (/product manager|product intern/.test(lower)) detected_target_role = "Product Management Intern";
  else detected_target_role = "Graduate Software Engineer";

  return {
    candidate_name,
    experience_level: /vac work|vacation work/.test(lower) ? "BSc IT · Vac Work" : /senior|staff/.test(lower) ? "Senior Engineer" : "Final-year BSc IT (SWE)",
    years_experience: /82\.4%/.test(lower) ? "82.4% avg · 14 distinctions" : "Top Projects & Coursework",
    location: /cape town/i.test(rawText) ? "Cape Town, Western Cape" : /pretoria/i.test(rawText) ? "Pretoria, Gauteng" : "Midrand, Gauteng",
    primary_skills,
    projects: projects.slice(0, 5),
    education: "BSc Information Technology (Software Engineering)",
    extraction_method: "Text extracted",
    projects_summary_line: `Extracted ${projects.length} projects (including ${projects[0].name}) and ${primary_skills.length} core skills.`,
    detected_target_company,
    detected_target_role,
    seniority_track: detectSeniorityTrack(detected_target_role, "", rawText),
  };
}

export function staticLoadSampleCV(): CVDocument {
  return {
    id: makeId(),
    filename: "Mbesa_Lephoto_Stripe_Data_Analyst_Intern_CV.pdf",
    file_type: "PDF",
    file_size_bytes: 98400,
    page_count: 3,
    raw_text: SAMPLE_CV_TEXT,
    candidate_profile: parseProfileFromText(SAMPLE_CV_TEXT),
    created_at: new Date().toISOString(),
  };
}

async function callBrowserGeminiJson(
  prompt: string,
  inlineFile?: { mimeType: string; data: string }
): Promise<Record<string, unknown> | null> {
  const gemKey = safeStorageGet<string>(STORAGE_GEMINI_KEY, "");
  if (!gemKey) return null;
  const parts: Record<string, unknown>[] = [{ text: prompt }];
  if (inlineFile) {
    parts.push({ inlineData: inlineFile });
  }
  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key=${encodeURIComponent(gemKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts }],
          generationConfig: { temperature: 0.25, responseMimeType: "application/json" },
        }),
      }
    );
    if (!res.ok) return null;
    const data = (await res.json()) as {
      candidates?: { content?: { parts?: { text?: string }[] } }[];
    };
    const raw = (data.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("").trim();
    const cleaned = raw.replace(/^```(?:json)?\s*|\s*```$/g, "");
    return JSON.parse(cleaned) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export async function staticUploadCVFile(file: File): Promise<CVDocument> {
  let rawText = "";
  try {
    const txt = await file.text();
    const cleaned = txt.replace(/[^\x20-\x7E\r\n]/g, " ").replace(/\s{3,}/g, "\n").trim();
    rawText = cleaned.length > 80 ? cleaned.slice(0, 12000) : SAMPLE_CV_TEXT;
  } catch {
    rawText = SAMPLE_CV_TEXT;
  }
  let profile = parseProfileFromText(rawText);

  const gemKey = safeStorageGet<string>(STORAGE_GEMINI_KEY, "");
  if (gemKey && (file.type === "application/pdf" || file.type.startsWith("image/") || file.name.toLowerCase().endsWith(".pdf"))) {
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let binary = "";
      for (let i = 0; i < bytes.length; i += 8192) {
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      const b64 = btoa(binary);
      const mimeType = file.type || (file.name.toLowerCase().endsWith(".pdf") ? "application/pdf" : "image/png");
      const vision = await callBrowserGeminiJson(
        `Extract a strict JSON candidate profile from this CV. Keys: candidate_name, experience_level, years_experience, location, education, primary_skills (array), projects (array of {name, summary, technologies, scale_or_impact}), projects_summary_line, detected_target_company, detected_target_role, seniority_track (vac_work|intern_grad|junior|mid_senior). Never use em dashes.`,
        { mimeType, data: b64 }
      );
      if (vision && typeof vision.candidate_name === "string") {
        profile = {
          ...profile,
          ...(vision as unknown as CandidateProfile),
          extraction_method: "Text extracted",
        };
      }
    } catch {
      // fall back cleanly to local extraction
    }
  }

  const ext = (file.name.split(".").pop() || "PDF").toUpperCase();
  return {
    id: makeId(),
    filename: file.name,
    file_type: ext.slice(0, 4),
    file_size_bytes: file.size || 64000,
    page_count: Math.max(1, Math.min(4, Math.ceil((file.size || 50000) / 35000))),
    raw_text: rawText,
    candidate_profile: { ...profile, extraction_method: "Text extracted" },
    created_at: new Date().toISOString(),
  };
}

export function staticGetEngineStatus(): EngineSettingsStatus {
  const gemKey = safeStorageGet<string>(STORAGE_GEMINI_KEY, "");
  return {
    llm: gemKey
      ? { provider: "gemini", model: "gemini-3.1-flash-lite", frontier_enabled: true }
      : { provider: "browser_coach", model: "company-rubric-engine", frontier_enabled: false },
    stt: { provider: "browser_live", model: "web-speech-verbatim", cloud_verbatim_enabled: false },
    tts: { provider: "browser_speech", model: "web-speech-synthesis" },
    keys_configured: { GEMINI_API_KEY: Boolean(gemKey) },
    models: { GEMINI_MODEL: "gemini-3.1-flash-lite" },
  };
}

export function staticUpdateEngineKeys(payload: Record<string, string>): EngineSettingsStatus {
  if (payload.GEMINI_API_KEY) {
    safeStorageSet(STORAGE_GEMINI_KEY, payload.GEMINI_API_KEY.trim());
  }
  return staticGetEngineStatus();
}

export async function staticCreateSession(payload: {
  cv_document_id?: string | null;
  cv_raw_text?: string;
  candidate_profile?: CandidateProfile;
  company_name: string;
  target_role: string;
  job_description: string;
  round_focus?: string;
  question_count?: number;
}): Promise<InterviewSession> {
  const profile = payload.candidate_profile || parseProfileFromText(payload.cv_raw_text || SAMPLE_CV_TEXT);
  const research = staticResearchCompany(payload.company_name, payload.target_role, payload.job_description, profile.experience_level);
  const leadProj = profile.projects?.[0]?.name || "your core software project";
  const secondProj = profile.projects?.[1]?.name || leadProj;
  const topLc = research.coding_and_leetcode_patterns?.[0] || "Two Sum / Hash Map lookup (LeetCode 1)";
  const rubric = research.company_grading_rubric || research.evaluation_bar;
  const qCount = Math.min(8, Math.max(5, payload.question_count || 6));

  const templateQuestions: Omit<SessionQuestion, "id">[] = [
    {
      order_index: 0,
      short_title: "Tell me about yourself",
      category: "Warm-up",
      question_text: `Walk me through your background, why ${research.company_name}'s ${research.role_label} role stands out to you, and one project you are proudest of shipping.`,
      source_attribution: `Real ${research.company_name} loop  ·  Opening calibration`,
      guidance_cues: ["Connect your story to this role in 90 seconds", `Highlight ${leadProj}`, `Explain what excites you about ${research.company_name}`],
      evaluation_focus: rubric.slice(0, 3),
      status: "in_progress",
      latest_attempt: null,
    },
    {
      order_index: 1,
      short_title: `${research.company_name} coding walkthrough`,
      category: "Coding & algorithms",
      question_text: `Walk me out loud through solving a core ${research.company_name} coding/technical problem (${topLc}). State your brute-force baseline, how you optimize data structures and Big-O complexity, and key edge cases.`,
      source_attribution: `Real ${research.company_name} loop  ·  Coding / LeetCode round`,
      guidance_cues: ["Clarify inputs and brute-force baseline first", "Optimize data structure & state Big-O", "Dry-run edge cases out loud"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
    {
      order_index: 2,
      short_title: smartTrim(`Deep dive: ${leadProj}`, 34),
      category: "Project deep dive",
      question_text: `Walk me through how you designed and tested ${leadProj}. Where did you hit the trickiest bottleneck or bug, and why did you choose that architecture?`,
      source_attribution: `Based on your CV  ·  ${leadProj}`,
      guidance_cues: ["Start with a 30-sec system overview", "Explain concrete data/architecture choices", "Close with verified metrics or impact"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
    {
      order_index: 3,
      short_title: `${research.role_label.split(" ")[0]} design scenario`,
      category: "System design",
      question_text: `Design a reliable workflow core to ${research.company_name}'s ${research.role_label} team. Walk through data schema, concurrency or error handling, and failure recovery.`,
      source_attribution: `${research.company_name} · ${research.archetype_short_label} round`,
      guidance_cues: ["Clarify constraints and target scale first", "Draw clean boundaries between storage and APIs", "Address retries, concurrency, and failure modes"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
    {
      order_index: 4,
      short_title: `${research.company_name} culture & feedback`,
      category: "Behavioral",
      question_text: `Tell me about a time you faced a difficult technical blocker or received critical feedback on your work. What did YOU specifically do to adapt and deliver?`,
      source_attribution: `Real ${research.company_name} loop  ·  Culture & ownership bar`,
      guidance_cues: ["Keep Situation & Task under 30 seconds", "Emphasize your personal actions ('I' not 'we')", "Close with measured outcome & reflection"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
    {
      order_index: 5,
      short_title: "A decision you would revisit",
      category: "Project deep dive",
      question_text: `Looking back at ${secondProj}, what is one design or implementation choice you would change today if usage grew 10x?`,
      source_attribution: `Based on your CV  ·  Judgment probe`,
      guidance_cues: ["Be candid about the initial constraint", "Identify what breaks first at 10x", "Describe your clean refactor plan"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
    {
      order_index: 6,
      short_title: "Live debugging triage",
      category: "Technical depth",
      question_text: `Suppose a critical service owned by ${research.company_name}'s team suddenly experiences elevated failures for 10% of requests. Walk me through your first 15 minutes of debugging.`,
      source_attribution: `${research.company_name} · Production troubleshooting`,
      guidance_cues: ["Assess blast radius and check recent deploys/logs", "Form isolated hypotheses", "Stabilize safely before root-cause patching"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
    {
      order_index: 7,
      short_title: "Stakeholder alignment trade-off",
      category: "Behavioral",
      question_text: "Tell me about a time you had to align teammates or stakeholders with competing priorities under a tight deadline. How did you reach agreement?",
      source_attribution: `Real ${research.company_name} loop  ·  Collaboration round`,
      guidance_cues: ["Explain both sides objectively", "Show how you used data or an MVP prototype", "Quantify the final team delivery"],
      evaluation_focus: rubric.slice(0, 3),
      status: "up_next",
      latest_attempt: null,
    },
  ];

  let questions: SessionQuestion[] = templateQuestions.slice(0, qCount).map((q, idx) => ({
    ...q,
    order_index: idx,
    id: makeId(),
  }));

  const geminiPack = await callBrowserGeminiJson(
    `Create a tailored ${qCount}-question mock interview for ${research.company_name} (${research.role_label}, track ${research.seniority_track}). Rubric: ${JSON.stringify(rubric)}. Coding patterns: ${JSON.stringify(research.coding_and_leetcode_patterns)}. Candidate CV projects: ${JSON.stringify(profile.projects)}. Job Description: ${payload.job_description.slice(0, 1600)}. Never use em dashes. Return strict JSON: {"questions": [{"short_title": "...", "category": "Warm-up|Coding & algorithms|Project deep dive|System design|Behavioral|Technical depth", "question_text": "...", "source_attribution": "...", "guidance_cues": ["...", "...", "..."], "evaluation_focus": ["...", "..."]}]}`
  );
  if (geminiPack && Array.isArray(geminiPack.questions) && geminiPack.questions.length >= 4) {
    questions = (geminiPack.questions as Record<string, unknown>[]).slice(0, qCount).map((gq, idx) => ({
      id: makeId(),
      order_index: idx,
      short_title: cleanDashes(String(gq.short_title || `Question ${idx + 1}`)),
      category: cleanDashes(String(gq.category || "Technical depth")),
      question_text: cleanDashes(String(gq.question_text || "")),
      source_attribution: cleanDashes(String(gq.source_attribution || `Real ${research.company_name} loop`)),
      guidance_cues: Array.isArray(gq.guidance_cues) ? gq.guidance_cues.slice(0, 3).map((x) => cleanDashes(String(x))) : ["Structure clearly", "Address edge cases", "Close with outcome"],
      evaluation_focus: Array.isArray(gq.evaluation_focus) ? gq.evaluation_focus.slice(0, 3).map((x) => cleanDashes(String(x))) : rubric.slice(0, 3),
      status: idx === 0 ? "in_progress" : "up_next",
      latest_attempt: null,
    }));
  }

  const now = new Date().toISOString();
  const session: InterviewSession = {
    id: makeId(),
    cv_document_id: payload.cv_document_id || null,
    company_name: research.company_name,
    target_role: research.role_label,
    round_focus: payload.round_focus || "full_loop",
    job_description: payload.job_description,
    jd_signals: research.role_core_topics.slice(0, 3).map((t) => smartTrim(t, 28)),
    company_research: research,
    candidate_profile: profile,
    explore_pillars: research.explore_pillars || [],
    status: "in_progress",
    current_question_index: 0,
    overall_score: null,
    questions,
    created_at: now,
    updated_at: now,
  };

  const existing = safeStorageGet<InterviewSession[]>(STORAGE_SESSIONS, []);
  safeStorageSet(STORAGE_SESSIONS, [session, ...existing.slice(0, 19)]);
  return session;
}

export function staticListSessions(): InterviewSession[] {
  return safeStorageGet<InterviewSession[]>(STORAGE_SESSIONS, []);
}

export function staticGetSession(sessionId: string): InterviewSession {
  const found = staticListSessions().find((s) => s.id === sessionId);
  if (!found) throw new Error("Session not found in local workspace.");
  return found;
}

export function staticDeleteSession(sessionId: string): void {
  const filtered = staticListSessions().filter((s) => s.id !== sessionId);
  safeStorageSet(STORAGE_SESSIONS, filtered);
}

export async function staticEvaluateQuestionAnswer(params: {
  sessionId: string;
  questionId: string;
  fallbackTranscript: string;
  durationSeconds: number;
}): Promise<QuestionAttempt> {
  const sessions = staticListSessions();
  const sIdx = sessions.findIndex((s) => s.id === params.sessionId);
  if (sIdx < 0) throw new Error("Session not found.");
  const session = sessions[sIdx];
  const qIdx = session.questions.findIndex((q) => q.id === params.questionId);
  if (qIdx < 0) throw new Error("Question not found.");
  const question = session.questions[qIdx];

  const transcript = params.fallbackTranscript.trim() || "Walked through high-level context and core implementation steps.";
  const words = transcript.match(/[A-Za-z0-9']+/g) || [];
  const wc = words.length;
  const dur = Math.max(params.durationSeconds || 15, 5);
  const wpm = Math.round(wc / Math.max(dur / 60, 0.08));

  const fillers: Record<string, number> = {};
  for (const w of words.map((x) => x.toLowerCase())) {
    if (["um", "uh", "basically", "literally", "actually", "like"].includes(w)) {
      fillers[w] = (fillers[w] || 0) + 1;
    }
  }
  const fillerCount = Object.values(fillers).reduce((a, b) => a + b, 0);
  const fillerPerMin = Number((fillerCount / Math.max(dur / 60, 0.1)).toFixed(1));

  const hedging: string[] = [];
  for (const pat of [/i think maybe/i, /i'?m not sure/i, /i guess/i, /if that makes sense/i]) {
    const m = transcript.match(pat);
    if (m) hedging.push(m[0]);
  }

  const lower = transcript.toLowerCase();
  const techHits = ["latency", "sql", "index", "o(", "complexity", "edge case", "hash", "queue", "idempoten", "oop", "solid", "lock", "metric", "test"].filter(
    (t) => lower.includes(t)
  ).length;
  const commScore = Math.max(55, Math.min(92, 82 - (fillerPerMin > 3 ? 8 : 0) - (wc < 30 ? 12 : 0)));
  const techScore = Math.max(50, Math.min(92, 56 + techHits * 6 + (/\d/.test(lower) ? 6 : 0)));
  const structScore = Math.max(54, Math.min(90, 62 + (/first|then|finally|because|result/.test(lower) ? 14 : 0)));
  const confScore = Math.max(52, Math.min(92, 84 - hedging.length * 6 - Math.round(fillerPerMin * 2)));
  const overall = Math.round(0.25 * commScore + 0.35 * techScore + 0.2 * structScore + 0.2 * confScore);

  const research = session.company_research;
  const primaryRubric = research.company_grading_rubric?.[0] || research.evaluation_bar[0] || "Clear technical depth";
  const expectedStruct = research.expected_answer_structure || "Context -> Core logic -> Edge cases -> Impact";

  const metrics: DeliveryMetrics = {
    duration_seconds: dur,
    duration_formatted: `${Math.floor(dur / 60)}:${String(Math.round(dur % 60)).padStart(2, "0")}`,
    word_count: wc,
    speaking_pace_wpm: wpm,
    pace_label: wpm > 175 ? "Too fast" : wpm < 100 ? "Measured" : "Steady",
    pace_status: wpm > 175 ? "warn" : "good",
    filler_count: fillerCount,
    filler_per_min: fillerPerMin,
    filler_label: fillerPerMin <= 2 ? "Clean" : fillerPerMin <= 4 ? "Moderate" : "Reduce",
    filler_status: fillerPerMin <= 2 ? "good" : "warn",
    filler_breakdown: fillers,
    longest_pause_sec: 1.2,
    pause_label: "Smooth",
    pause_status: "good",
    awkward_pauses: [],
    hedging_phrases: hedging,
    annotated_transcript: transcript,
    stt_provider: "browser_live",
    has_word_timestamps: false,
  };

  const studyItems: StudyMaterialItem[] = [
    {
      topic: `${research.company_name} rubric focus`,
      subtitle: `${research.role_label}: ${smartTrim(primaryRubric, 46)}`,
      why: `Targets the exact marking signal prioritized in ${research.company_name}'s loop.`,
      search_query_or_resource: `${research.company_name} ${research.role_label} interview preparation`,
      resource_url: `https://www.google.com/search?q=${encodeURIComponent(`${research.company_name} ${research.role_label} interview questions`)}`,
    },
  ];

  let evaluation: EvaluationResult = {
    headline: cleanDashes(overall >= 80 ? `Strong fit for ${research.company_name}.` : `Good foundation for ${research.company_name}. Sharpen structure.`),
    scores: {
      communication: commScore,
      communication_note: commScore >= 80 ? "Clear and well-paced" : "Tighten clarity & pacing",
      technical_depth: techScore,
      technical_depth_note: `Aligned to ${research.company_name} bar`,
      structure: structScore,
      structure_note: "Match expected company flow",
      confidence: confScore,
      confidence_note: hedging.length ? "Trim hedging phrases" : "Steady vocal delivery",
      overall,
    },
    gaps: [
      { index: "01", title: `Follow ${research.company_name}'s flow`, detail: cleanDashes(`Structure crisply as: ${expectedStruct}.`) },
      { index: "02", title: `Hit ${research.company_name}'s rubric`, detail: cleanDashes(`Explicitly demonstrate: ${primaryRubric}.`) },
    ],
    what_went_wrong: cleanDashes(`Open with the high-level frame before implementation details so ${research.company_name} interviewers can score your structure immediately.`),
    what_was_missing: cleanDashes(`Stronger explicit proof of ${primaryRubric}.`),
    how_to_fix: cleanDashes(`Use ${research.company_name}'s expected pattern (${expectedStruct}) and quantify results.`),
    fix_formula: cleanDashes(expectedStruct),
    sample_strong_answer: cleanDashes(`"At ${research.company_name}, I would first clarify the constraints and core objective, then walk systematically through the trade-offs, edge cases, and quantified impact."`),
    sample_paragraphs: [
      cleanDashes(`"At ${research.company_name}, I would start by stating the constraints, target scale, and assumptions clearly so we align on scope before choosing data structures or architecture.`),
      cleanDashes(`Next, building on experience from ${session.candidate_profile.projects?.[0]?.name || "my projects"}, I would walk step by step through the core implementation, highlighting complexity, security/concurrency trade-offs, and failure boundaries.`),
      `Finally, I would dry-run boundary edge cases and verify measurable outcomes against customer and reliability metrics."`,
    ],
    hedging_phrases_found: hedging,
    study_material: studyItems,
    llm_provider: "browser_coach",
    llm_model: "company-rubric-engine",
  };

  const gemEval = await callBrowserGeminiJson(
    `Evaluate this spoken answer for ${research.company_name} (${research.role_label}, rubric: ${JSON.stringify(research.company_grading_rubric)}, expected structure: ${expectedStruct}). Question: ${question.question_text}. Telemetry: ${wpm} WPM, ${fillerPerMin} fillers/min. Transcript: ${transcript}. Never use em dashes. Return strict JSON: {"headline": "...", "scores": {"communication": 0-100, "communication_note": "...", "technical_depth": 0-100, "technical_depth_note": "...", "structure": 0-100, "structure_note": "...", "confidence": 0-100, "confidence_note": "...", "overall": 0-100}, "gaps": [{"index": "01", "title": "...", "detail": "..."}, {"index": "02", "title": "...", "detail": "..."}], "what_went_wrong": "...", "what_was_missing": "...", "how_to_fix": "...", "fix_formula": "...", "sample_strong_answer": "...", "sample_paragraphs": ["...", "...", "..."], "hedging_phrases_found": [], "study_material": [{"topic": "...", "subtitle": "...", "why": "...", "search_query_or_resource": "..."}]}`
  );
  if (gemEval && gemEval.scores && typeof gemEval.what_went_wrong === "string") {
    const rawStudies = Array.isArray(gemEval.study_material) ? (gemEval.study_material as StudyMaterialItem[]) : studyItems;
    evaluation = {
      ...(gemEval as unknown as EvaluationResult),
      study_material: rawStudies.map((s) => ({
        ...s,
        resource_url: s.resource_url || `https://www.google.com/search?q=${encodeURIComponent(s.search_query_or_resource || s.topic)}`,
      })),
      llm_provider: "gemini",
      llm_model: "gemini-3.1-flash-lite",
    };
  }

  const attempt: QuestionAttempt = {
    id: makeId(),
    attempt_number: (question.latest_attempt?.attempt_number || 0) + 1,
    duration_seconds: dur,
    stt_provider: "browser_live",
    transcript_verbatim: transcript,
    transcript_clean: transcript,
    word_timestamps: [],
    delivery_metrics: metrics,
    evaluation,
    created_at: new Date().toISOString(),
  };

  session.questions[qIdx] = { ...question, status: "completed", latest_attempt: attempt };
  if (qIdx + 1 < session.questions.length && session.questions[qIdx + 1].status === "up_next") {
    session.questions[qIdx + 1].status = "in_progress";
    session.current_question_index = qIdx + 1;
  }
  const scores = session.questions.map((q) => q.latest_attempt?.evaluation.scores.overall).filter((n): n is number => typeof n === "number");
  session.overall_score = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
  if (session.questions.every((q) => q.status === "completed")) session.status = "completed";
  session.updated_at = new Date().toISOString();
  sessions[sIdx] = session;
  safeStorageSet(STORAGE_SESSIONS, sessions);

  const studyList = safeStorageGet<StudyPlanRecord[]>(STORAGE_STUDY, []);
  const newStudy: StudyPlanRecord = {
    id: makeId(),
    session_id: session.id,
    company_name: session.company_name,
    target_role: session.target_role,
    topic: studyItems[0].topic,
    subtitle: studyItems[0].subtitle,
    why: studyItems[0].why,
    search_query_or_resource: studyItems[0].search_query_or_resource,
    resource_url: studyItems[0].resource_url,
    completed: false,
    created_at: new Date().toISOString(),
  };
  safeStorageSet(STORAGE_STUDY, [newStudy, ...studyList.slice(0, 30)]);
  return attempt;
}

export function staticFetchStudyPlan(): StudyPlanRecord[] {
  return safeStorageGet<StudyPlanRecord[]>(STORAGE_STUDY, []);
}

export function staticToggleStudyPlanItem(itemId: string, completed: boolean): StudyPlanRecord {
  const list = staticFetchStudyPlan();
  const updated = list.map((item) => (item.id === itemId ? { ...item, completed } : item));
  safeStorageSet(STORAGE_STUDY, updated);
  return updated.find((i) => i.id === itemId) || list[0];
}

export function staticFetchOverview(): OverviewStats {
  const sessions = staticListSessions();
  const evaluated = sessions.flatMap((s) => s.questions.map((q) => q.latest_attempt).filter((a): a is QuestionAttempt => Boolean(a)));
  const avg = (fn: (a: QuestionAttempt) => number) =>
    evaluated.length ? Math.round(evaluated.reduce((sum, a) => sum + fn(a), 0) / evaluated.length) : 0;

  return {
    sessions_this_week: sessions.length,
    weekly_goal: 3,
    total_sessions: sessions.length,
    total_answers_evaluated: evaluated.length,
    average_overall: evaluated.length ? avg((a) => a.evaluation.scores.overall) : null,
    average_scores: {
      communication: avg((a) => a.evaluation.scores.communication),
      technical_depth: avg((a) => a.evaluation.scores.technical_depth),
      structure: avg((a) => a.evaluation.scores.structure),
      confidence: avg((a) => a.evaluation.scores.confidence),
    },
    recent_sessions: sessions.slice(0, 5).map((s) => ({
      id: s.id,
      company_name: s.company_name,
      target_role: s.target_role,
      status: s.status,
      overall_score: s.overall_score,
      completed_questions: s.questions.filter((q) => q.status === "completed").length,
      total_questions: s.questions.length,
      created_at: s.created_at,
      updated_at: s.updated_at,
    })),
    active_llm: staticGetEngineStatus().llm,
    active_stt: staticGetEngineStatus().stt,
    active_tts: staticGetEngineStatus().tts,
  };
}
