"use client";

import React, { useCallback, useEffect, useState } from "react";
import AnswerReviewScreen from "@/components/AnswerReviewScreen";
import HelpModal from "@/components/HelpModal";
import OverviewView from "@/components/OverviewView";
import SessionsView from "@/components/SessionsView";
import SetupScreen from "@/components/SetupScreen";
import Sidebar from "@/components/Sidebar";
import StudyPlanView from "@/components/StudyPlanView";
import TopBar from "@/components/TopBar";
import VoicePracticeScreen from "@/components/VoicePracticeScreen";
import {
  createSession,
  deleteSession,
  evaluateQuestionAnswer,
  fetchArchetypes,
  fetchEngineStatus,
  fetchOverview,
  fetchStudyPlan,
  getSession,
  listSessions,
  loadSampleCV,
  toggleStudyPlanItem,
} from "@/lib/api";
import type {
  ArchetypeOverview,
  CVDocument,
  EngineSettingsStatus,
  InterviewSession,
  KnownCompanyItem,
  NavTab,
  OverviewStats,
  PracticeStage,
  StudyPlanRecord,
} from "@/types/rehearse";

const DEFAULT_JD =
  "Join Stripe as a Data Analyst Intern working across global programmable financial infrastructure and risk systems. Build scalable SQL and Python data pipelines, design metrics semantic layers and executive dashboards, analyze payment conversion and return friction, and partner with product and engineering teams.";

export default function RehearseApp() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [activeTab, setActiveTab] = useState<NavTab>("practice");
  const [practiceStage, setPracticeStage] = useState<PracticeStage>("setup");

  // Setup state
  const [cvDoc, setCvDoc] = useState<CVDocument | null>(null);
  const [companyName, setCompanyName] = useState("Stripe");
  const [targetRole, setTargetRole] = useState("Data Analyst Intern");
  const [jobDescription, setJobDescription] = useState(DEFAULT_JD);
  const [roundFocus, setRoundFocus] = useState("full_loop");
  const [questionCount, setQuestionCount] = useState(6);
  const [generating, setGenerating] = useState(false);
  const [setupError, setSetupError] = useState("");

  // Active interview state
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [questionIndex, setQuestionIndex] = useState(0);

  // Workspace data
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [studyPlan, setStudyPlan] = useState<StudyPlanRecord[]>([]);
  const [archetypes, setArchetypes] = useState<ArchetypeOverview[]>([]);
  const [knownCompanies, setKnownCompanies] = useState<KnownCompanyItem[]>([]);
  const [engineStatus, setEngineStatus] = useState<EngineSettingsStatus | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  // Sync light/dark theme onto <html>
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Keep workspace scrolled to the top on view/stage transitions
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  }, [activeTab, practiceStage, questionIndex]);

  const refreshWorkspace = useCallback(async () => {
    try {
      const [ov, sessList, studyList, eng] = await Promise.all([
        fetchOverview(),
        listSessions(),
        fetchStudyPlan(),
        fetchEngineStatus(),
      ]);
      setOverview(ov);
      setSessions(sessList);
      setStudyPlan(studyList);
      setEngineStatus(eng);
    } catch {
      // Backend may still be booting
    }
  }, []);

  // Initial load: workspace stats, curated archetypes, and sample CV ready-state (matching Figma 01)
  useEffect(() => {
    refreshWorkspace();
    fetchArchetypes()
      .then((res) => {
        setArchetypes(res.archetypes);
        setKnownCompanies(res.companies);
      })
      .catch(() => {});
    loadSampleCV()
      .then((doc) => setCvDoc(doc))
      .catch(() => {});
  }, [refreshWorkspace]);

  async function handleGenerateInterview() {
    setGenerating(true);
    setSetupError("");
    try {
      const created = await createSession({
        cv_document_id: cvDoc?.id || null,
        cv_raw_text: cvDoc?.raw_text,
        candidate_profile: cvDoc?.candidate_profile,
        company_name: companyName.trim(),
        target_role: targetRole.trim(),
        job_description: jobDescription.trim(),
        round_focus: roundFocus,
        question_count: questionCount,
      });
      setActiveSession(created);
      setQuestionIndex(0);
      setPracticeStage("voice");
      setActiveTab("practice");
      refreshWorkspace();
    } catch (err) {
      setSetupError(
        err instanceof Error
          ? err.message
          : "Could not generate interview. Make sure the FastAPI backend is running on port 8000."
      );
    } finally {
      setGenerating(false);
    }
  }

  async function handleSubmitAnswer(params: {
    questionId: string;
    audioBlob: Blob | null;
    transcript: string;
    durationSeconds: number;
  }) {
    if (!activeSession) return;
    await evaluateQuestionAnswer({
      sessionId: activeSession.id,
      questionId: params.questionId,
      audioBlob: params.audioBlob,
      fallbackTranscript: params.transcript,
      durationSeconds: params.durationSeconds,
    });
    const updatedSession = await getSession(activeSession.id);
    setActiveSession(updatedSession);
    setPracticeStage("review");
    refreshWorkspace();
  }

  function handleSelectQuestion(idx: number, openReviewIfDone = false) {
    setQuestionIndex(idx);
    const q = activeSession?.questions[idx];
    if (openReviewIfDone && q?.latest_attempt) {
      setPracticeStage("review");
    } else {
      setPracticeStage("voice");
    }
  }

  function handleResumeSession(session: InterviewSession) {
    setActiveSession(session);
    const firstPending = session.questions.findIndex((q) => q.status !== "completed");
    if (firstPending >= 0) {
      setQuestionIndex(firstPending);
      setPracticeStage("voice");
    } else {
      setQuestionIndex(Math.max(0, session.questions.length - 1));
      setPracticeStage("review");
    }
    setActiveTab("practice");
  }

  async function handleOpenSessionById(sessionId: string) {
    try {
      const s = await getSession(sessionId);
      handleResumeSession(s);
    } catch {
      // ignore
    }
  }

  async function handleDeleteSession(sessionId: string) {
    await deleteSession(sessionId);
    if (activeSession?.id === sessionId) {
      setActiveSession(null);
      setPracticeStage("setup");
    }
    refreshWorkspace();
  }

  async function handleToggleStudy(itemId: string, completed: boolean) {
    await toggleStudyPlanItem(itemId, completed);
    refreshWorkspace();
  }

  function handleStartFreshInterview(presetCompany?: string) {
    if (presetCompany) {
      setCompanyName(presetCompany);
    }
    setActiveSession(null);
    setPracticeStage("setup");
    setActiveTab("practice");
  }

  const candidateName = cvDoc?.candidate_profile?.candidate_name || "Mbesa Lephoto";

  const handleCvLoaded = useCallback((doc: CVDocument) => {
    setCvDoc(doc);
    const detectedCompany = doc.candidate_profile?.detected_target_company?.trim();
    const detectedRole = doc.candidate_profile?.detected_target_role?.trim();
    if (detectedCompany) {
      setCompanyName(detectedCompany);
    }
    if (detectedRole) {
      setTargetRole(detectedRole);
    }
  }, []);

  return (
    <div
      className="min-h-screen flex"
      style={{ backgroundColor: "var(--bg-canvas)", color: "var(--text-primary)" }}
    >
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (tab === "practice" && !activeSession) {
            setPracticeStage("setup");
          }
        }}
        sessionsThisWeek={overview?.sessions_this_week ?? 0}
        weeklyGoal={overview?.weekly_goal ?? 3}
        theme={theme}
        onChangeTheme={setTheme}
        candidateName={candidateName}
      />

      <div className="flex-1 min-w-0 flex flex-col min-h-screen">
        <TopBar
          activeTab={activeTab}
          practiceStage={practiceStage}
          engineStatus={engineStatus}
          onOpenHelp={() => setHelpOpen(true)}
        />

        <main className="flex-1 px-[24px] sm:px-[36px] lg:px-[48px] py-[36px]">
          {activeTab === "overview" && (
            <OverviewView
              stats={overview}
              archetypes={archetypes}
              onStartNewInterview={handleStartFreshInterview}
              onOpenSession={handleOpenSessionById}
            />
          )}

          {activeTab === "practice" && practiceStage === "setup" && (
            <SetupScreen
              cvDoc={cvDoc}
              onCvLoaded={handleCvLoaded}
              companyName={companyName}
              onCompanyNameChange={setCompanyName}
              targetRole={targetRole}
              onTargetRoleChange={setTargetRole}
              jobDescription={jobDescription}
              onJobDescriptionChange={setJobDescription}
              roundFocus={roundFocus}
              onRoundFocusChange={setRoundFocus}
              questionCount={questionCount}
              onQuestionCountChange={setQuestionCount}
              knownCompanies={knownCompanies}
              onGenerateInterview={handleGenerateInterview}
              generating={generating}
              error={setupError}
            />
          )}

          {activeTab === "practice" && practiceStage === "voice" && activeSession && (
            <VoicePracticeScreen
              session={activeSession}
              questionIndex={questionIndex}
              onSelectQuestion={handleSelectQuestion}
              onSubmitAnswer={handleSubmitAnswer}
              onSaveAndExit={() => {
                setActiveTab("sessions");
                refreshWorkspace();
              }}
            />
          )}

          {activeTab === "practice" && practiceStage === "review" && activeSession && (
            <AnswerReviewScreen
              session={activeSession}
              questionIndex={questionIndex}
              onRetryQuestion={() => setPracticeStage("voice")}
              onContinueNext={() => {
                const nextIdx = Math.min(
                  activeSession.questions.length - 1,
                  questionIndex + 1
                );
                setQuestionIndex(nextIdx);
                setPracticeStage("voice");
              }}
              onOpenStudyPlan={() => {
                refreshWorkspace();
                setActiveTab("study");
              }}
            />
          )}

          {activeTab === "sessions" && (
            <SessionsView
              sessions={sessions}
              onResumeSession={handleResumeSession}
              onDeleteSession={handleDeleteSession}
              onStartNew={() => handleStartFreshInterview()}
            />
          )}

          {activeTab === "study" && (
            <StudyPlanView
              items={studyPlan}
              onToggleItem={handleToggleStudy}
              onStartNew={() => handleStartFreshInterview()}
            />
          )}
        </main>
      </div>

      <HelpModal
        open={helpOpen}
        onClose={() => setHelpOpen(false)}
        engineStatus={engineStatus}
        onStatusUpdated={(status) => {
          setEngineStatus(status);
          refreshWorkspace();
        }}
      />
    </div>
  );
}
