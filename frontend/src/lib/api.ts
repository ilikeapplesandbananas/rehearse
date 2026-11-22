import type {
  ArchetypeOverview,
  CVDocument,
  CVPresetMeta,
  CandidateProfile,
  CompanyResearchResult,
  EngineSettingsStatus,
  InterviewSession,
  KnownCompanyItem,
  OverviewStats,
  QuestionAttempt,
  StudyPlanRecord,
} from "@/types/rehearse";
import {
  staticCreateSession,
  staticDeleteSession,
  staticEvaluateQuestionAnswer,
  staticFetchArchetypes,
  staticFetchOverview,
  staticFetchStudyPlan,
  staticGetEngineStatus,
  staticGetSession,
  staticListSessions,
  staticLoadSampleCV,
  staticResearchCompany,
  staticToggleStudyPlanItem,
  staticUpdateEngineKeys,
  staticUploadCVFile,
} from "@/lib/static-fallback";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8008";

function shouldUseStaticDirect(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  const isLocalHost = host === "localhost" || host === "127.0.0.1";
  const pointsToLocalApi =
    API_BASE.includes("localhost") || API_BASE.includes("127.0.0.1");
  return !isLocalHost && pointsToLocalApi;
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore json parse failure
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function withFallback<T>(
  remoteCall: () => Promise<T>,
  fallbackCall: () => Promise<T> | T
): Promise<T> {
  if (shouldUseStaticDirect()) {
    return fallbackCall();
  }
  try {
    return await remoteCall();
  } catch (err) {
    // Only fall back on network/CORS outage; surface validation HTTP errors (4xx/422) from live backend
    if (err instanceof TypeError) {
      return fallbackCall();
    }
    throw err;
  }
}

export async function fetchOverview(): Promise<OverviewStats> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/overview`, { cache: "no-store" });
      return handleJson<OverviewStats>(res);
    },
    () => staticFetchOverview()
  );
}

export async function fetchEngineStatus(): Promise<EngineSettingsStatus> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/settings/status`, { cache: "no-store" });
      return handleJson<EngineSettingsStatus>(res);
    },
    () => staticGetEngineStatus()
  );
}

export async function updateEngineKeys(
  payload: Record<string, string>
): Promise<EngineSettingsStatus> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/settings/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return handleJson<EngineSettingsStatus>(res);
    },
    () => staticUpdateEngineKeys(payload)
  );
}

export async function uploadCVFile(file: File): Promise<CVDocument> {
  return withFallback(
    async () => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/cv/upload`, {
        method: "POST",
        body: form,
      });
      return handleJson<CVDocument>(res);
    },
    () => staticUploadCVFile(file)
  );
}

export async function loadSampleCV(): Promise<CVDocument> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/cv/sample`, { method: "POST" });
      return handleJson<CVDocument>(res);
    },
    () => staticLoadSampleCV()
  );
}

export async function fetchCVPresets(): Promise<{ presets: CVPresetMeta[] }> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/cv/presets`, { cache: "no-store" });
      return handleJson<{ presets: CVPresetMeta[] }>(res);
    },
    () => ({ presets: [] })
  );
}

export async function loadCVPreset(presetId: string): Promise<CVDocument> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/cv/preset/${encodeURIComponent(presetId)}`, {
        method: "POST",
      });
      return handleJson<CVDocument>(res);
    },
    () => staticLoadSampleCV()
  );
}

export async function deleteCV(docId: string): Promise<void> {
  if (shouldUseStaticDirect()) return;
  try {
    await fetch(`${API_BASE}/api/cv/${docId}`, { method: "DELETE" });
  } catch {
    // ignore
  }
}

export async function fetchArchetypes(): Promise<{
  archetypes: ArchetypeOverview[];
  companies: KnownCompanyItem[];
}> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/research/archetypes`, { cache: "no-store" });
      return handleJson(res);
    },
    () => staticFetchArchetypes()
  );
}

export async function researchCompany(
  company_name: string,
  target_role: string,
  job_description: string,
  force_live = false,
  experience_level = ""
): Promise<CompanyResearchResult> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/research/company`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company_name, target_role, job_description, force_live, experience_level }),
      });
      return handleJson<CompanyResearchResult>(res);
    },
    () => staticResearchCompany(company_name, target_role, job_description, experience_level)
  );
}

export async function createSession(payload: {
  cv_document_id?: string | null;
  cv_raw_text?: string;
  candidate_profile?: CandidateProfile;
  company_name: string;
  target_role: string;
  job_description: string;
  round_focus?: string;
  question_count?: number;
}): Promise<InterviewSession> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return handleJson<InterviewSession>(res);
    },
    () => staticCreateSession(payload)
  );
}

export async function listSessions(): Promise<InterviewSession[]> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/sessions`, { cache: "no-store" });
      return handleJson<InterviewSession[]>(res);
    },
    () => staticListSessions()
  );
}

export async function getSession(sessionId: string): Promise<InterviewSession> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, { cache: "no-store" });
      return handleJson<InterviewSession>(res);
    },
    () => staticGetSession(sessionId)
  );
}

export async function deleteSession(sessionId: string): Promise<void> {
  return withFallback(
    async () => {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
    },
    () => staticDeleteSession(sessionId)
  );
}

export async function evaluateQuestionAnswer(params: {
  sessionId: string;
  questionId: string;
  audioBlob: Blob | null;
  fallbackTranscript: string;
  durationSeconds: number;
}): Promise<QuestionAttempt> {
  return withFallback(
    async () => {
      const form = new FormData();
      if (params.audioBlob && params.audioBlob.size > 0) {
        const ext = params.audioBlob.type.includes("mp4")
          ? "m4a"
          : params.audioBlob.type.includes("ogg")
          ? "ogg"
          : "webm";
        form.append("audio", params.audioBlob, `answer.${ext}`);
      }
      form.append("fallback_transcript", params.fallbackTranscript);
      form.append("duration_seconds", String(params.durationSeconds));

      const res = await fetch(
        `${API_BASE}/api/sessions/${params.sessionId}/questions/${params.questionId}/evaluate`,
        {
          method: "POST",
          body: form,
        }
      );
      return handleJson<QuestionAttempt>(res);
    },
    () =>
      staticEvaluateQuestionAnswer({
        sessionId: params.sessionId,
        questionId: params.questionId,
        fallbackTranscript: params.fallbackTranscript,
        durationSeconds: params.durationSeconds,
      })
  );
}

export async function fetchStudyPlan(): Promise<StudyPlanRecord[]> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/study-plan`, { cache: "no-store" });
      return handleJson<StudyPlanRecord[]>(res);
    },
    () => staticFetchStudyPlan()
  );
}

export async function toggleStudyPlanItem(
  itemId: string,
  completed: boolean
): Promise<StudyPlanRecord> {
  return withFallback(
    async () => {
      const res = await fetch(`${API_BASE}/api/study-plan/${itemId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ completed }),
      });
      return handleJson<StudyPlanRecord>(res);
    },
    () => staticToggleStudyPlanItem(itemId, completed)
  );
}

export async function fetchNeuralTTS(text: string): Promise<Blob | null> {
  if (shouldUseStaticDirect()) return null;
  try {
    const res = await fetch(`${API_BASE}/api/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return null;
    return await res.blob();
  } catch {
    return null;
  }
}
