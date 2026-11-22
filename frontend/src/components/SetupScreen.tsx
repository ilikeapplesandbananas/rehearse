"use client";

import React, { useEffect, useRef, useState } from "react";
import { loadSampleCV, researchCompany, uploadCVFile } from "@/lib/api";
import type {
  CVDocument,
  CompanyResearchResult,
  KnownCompanyItem,
} from "@/types/rehearse";

interface SetupScreenProps {
  cvDoc: CVDocument | null;
  onCvLoaded: (doc: CVDocument) => void;
  companyName: string;
  onCompanyNameChange: (v: string) => void;
  targetRole: string;
  onTargetRoleChange: (v: string) => void;
  jobDescription: string;
  onJobDescriptionChange: (v: string) => void;
  roundFocus: string;
  onRoundFocusChange: (v: string) => void;
  questionCount: number;
  onQuestionCountChange: (n: number) => void;
  knownCompanies: KnownCompanyItem[];
  onGenerateInterview: () => Promise<void>;
  generating: boolean;
  error: string;
}

const ROLE_SUGGESTIONS = [
  "Vacation Work (Vac Work) Student",
  "Graduate Software Engineer",
  "Software Development Engineer Intern",
  "Data Analyst Intern",
  "Business Intelligence (BI) Intern",
  "AI Developer Intern",
  "Technical Project Manager",
  "Scrum Master",
  "Product Manager",
  "Product Management Intern",
  "Cybersecurity Analyst / Penetration Tester",
  "SOC Security Analyst",
  "Technical Business Analyst",
  "QA Automation / SDET Engineer",
  "Embedded Systems / IoT & Automation Engineer",
  "Technology Consulting Graduate (InfinityX)",
  "Visa Consulting & Analytics (VCA) Intern",
  "Data Center Operations (DCO) Tech Intern",
  "Business Developer Intern",
  "Backend Engineer",
  "Frontend Engineer",
  "Full-Stack Engineer",
  "Machine Learning / AI Engineer",
  "DevOps / SRE",
  "Data Engineer",
  "Enterprise .NET / Java Developer",
  "IT Systems & Operations Intern",
  "Application Security (AppSec) Engineer",
];

const ROUND_OPTIONS = [
  { id: "full_loop", label: "Full balanced loop" },
  { id: "system_design", label: "System design" },
  { id: "project_deep_dive", label: "Project deep dive" },
  { id: "technical_depth", label: "Coding & technical" },
  { id: "behavioral", label: "Behavioral / LPs" },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = Math.round(bytes / 1024);
  if (kb < 1024) return `${kb} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function extractClientJdSignals(jd: string, role: string): string[] {
  const lower = `${role} ${jd}`.toLowerCase();
  const pairs: [string, string[]][] = [
    ["API design", ["api", "rest", "graphql", "endpoint", "developer experience"]],
    ["OOP & clean code", ["oop", "solid", "java", "c#", ".net", "shesha", "vac work", "graduate"]],
    ["Security & triage", ["owasp", "siem", "pentest", "threat", "cyber", "popia", "zero-trust"]],
    ["Project & product", ["roadmap", "prd", "wbs", "critical path", "scrum", "circles", "cvp"]],
    ["Intralogistics & IoT", ["plc", "wms", "wcs", "intralogistics", "agv", "embedded", "kion", "dematic"]],
    ["Distributed systems", ["distributed", "scale", "queue", "kafka", "microservice", "consistency"]],
    ["Data & SQL", ["postgres", "sql", "schema", "database", "storage", "power bi", "dax", "star schema"]],
    ["ML & AI systems", ["llm", "machine learning", "inference", "rag", "model", "validation"]],
    ["Cloud & reliability", ["aws", "gcp", "azure", "kubernetes", "reliability", "latency"]],
    ["Ownership", ["ownership", "end-to-end", "autonomous", "bias for action", "lead"]],
    ["Frontend architecture", ["react", "next.js", "typescript", "browser", "ui"]],
  ];
  const out: string[] = [];
  for (const [label, kws] of pairs) {
    if (kws.some((k) => lower.includes(k))) out.push(label);
    if (out.length >= 4) break;
  }
  return out.length ? out : ["Technical depth", "Problem solving", "Ownership"];
}

export default function SetupScreen({
  cvDoc,
  onCvLoaded,
  companyName,
  onCompanyNameChange,
  targetRole,
  onTargetRoleChange,
  jobDescription,
  onJobDescriptionChange,
  roundFocus,
  onRoundFocusChange,
  questionCount,
  onQuestionCountChange,
  knownCompanies,
  onGenerateInterview,
  generating,
  error,
}: SetupScreenProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const [research, setResearch] = useState<CompanyResearchResult | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [showResearchDrawer, setShowResearchDrawer] = useState(false);
  const userEditedJdKeyRef = useRef<string>("");

  const profile = cvDoc?.candidate_profile;
  const expLevel = profile?.experience_level || "";
  const currentPairKey = `${companyName.trim().toLowerCase()}::${(targetRole.trim() || "Backend Engineer").toLowerCase()}::${expLevel}`;

  // Debounced live company + role + seniority interview research & auto-JD sync
  useEffect(() => {
    const trimmed = companyName.trim();
    if (trimmed.length < 2) {
      setResearch(null);
      return;
    }
    let cancelled = false;
    const roleVal = targetRole.trim() || "Backend Engineer";
    const pairKey = `${trimmed.toLowerCase()}::${roleVal.toLowerCase()}::${expLevel}`;

    const timer = setTimeout(async () => {
      setResearchLoading(true);
      try {
        const res = await researchCompany(trimmed, roleVal, "", false, expLevel);
        if (cancelled) return;
        setResearch(res);
        if (res.researched_job_description && userEditedJdKeyRef.current !== pairKey) {
          onJobDescriptionChange(res.researched_job_description);
        }
      } catch {
        // ignore transient lookup failures while typing
      } finally {
        if (!cancelled) setResearchLoading(false);
      }
    }, 320);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [companyName, targetRole, expLevel, onJobDescriptionChange]);

  async function handleFileSelect(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setUploadError("");
    try {
      const doc = await uploadCVFile(file);
      userEditedJdKeyRef.current = "";
      onCvLoaded(doc);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to parse CV file.");
    } finally {
      setUploading(false);
    }
  }

  async function handleLoadSample() {
    setUploading(true);
    setUploadError("");
    try {
      const doc = await loadSampleCV();
      userEditedJdKeyRef.current = "";
      onCvLoaded(doc);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Could not load sample CV.");
    } finally {
      setUploading(false);
    }
  }

  const jdSignals = extractClientJdSignals(jobDescription, targetRole);
  const leadProject = profile?.projects?.[0]?.name || "Your core CV project";
  const estMinutes = Math.round(questionCount * 3.3);

  const trimWords = (str: string, maxLen: number) => {
    if (str.length <= maxLen) return str;
    const cut = str.slice(0, maxLen).replace(/[,:;(\s]+[^,:\s]*$/, "").trim();
    return cut || str.slice(0, maxLen).trim();
  };

  const exploreItems = research?.explore_pillars?.length
    ? research.explore_pillars.map((ep, idx) => ({
        index: ep.index,
        title: idx === 0 && profile?.projects?.[0]?.name ? trimWords(leadProject, 34) : ep.title,
        desc: ep.description,
      }))
    : [
        {
          index: "01",
          title: trimWords(leadProject, 34),
          desc: "Architecture, scale, and the choices you made.",
        },
        {
          index: "02",
          title: `${(targetRole || "Backend").split(" ")[0]} fundamentals`,
          desc: research?.role_core_topics?.[0]
            ? `${trimWords(research.role_core_topics[0], 68)}.`
            : "Data structures, reliability, and practical trade-offs.",
        },
        {
          index: "03",
          title: research ? `How ${research.company_name} marks` : "How you work",
          desc: research
            ? `${research.archetype_short_label} · Ownership, trade-offs, and impact.`
            : "Ownership, collaboration, and impact.",
        },
      ];

  return (
    <div className="w-full max-w-[1128px] mx-auto">
      {/* Header */}
      <div className="mb-[28px]">
        <h1
          className="text-[32px] font-semibold leading-[1.3] tracking-[-0.02em]"
          style={{ color: "var(--text-primary)" }}
        >
          A little context. A better interview.
        </h1>
        <p
          className="text-[14px] font-normal mt-[8px]"
          style={{ color: "var(--text-secondary)" }}
        >
          Turn your experience and your next role into focused, realistic practice.
        </p>
      </div>

      {/* 3-Step Horizontal Bar */}
      <div className="grid grid-cols-3 gap-[24px] mb-[28px]">
        <div>
          <p
            className="text-[12px] font-semibold mb-[14px]"
            style={{ color: "var(--text-primary)" }}
          >
            01 &nbsp;&nbsp;Add your context
          </p>
          <div
            className="h-[3px] rounded-[2px]"
            style={{ backgroundColor: "var(--indicator-step-active)" }}
          />
        </div>
        <div>
          <p
            className="text-[12px] font-medium mb-[14px]"
            style={{ color: "var(--text-secondary)" }}
          >
            02 &nbsp;&nbsp;Practice out loud
          </p>
          <div
            className="h-[3px] rounded-[2px]"
            style={{ backgroundColor: "var(--border-default)" }}
          />
        </div>
        <div>
          <p
            className="text-[12px] font-medium mb-[14px]"
            style={{ color: "var(--text-secondary)" }}
          >
            03 &nbsp;&nbsp;Get your game plan
          </p>
          <div
            className="h-[3px] rounded-[2px]"
            style={{ backgroundColor: "var(--border-default)" }}
          />
        </div>
      </div>

      {/* Main 2-Column Grid matching Figma 700 / 404 ratio */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,700fr)_minmax(0,404fr)] gap-[24px] items-start">
        {/* Left Column */}
        <div className="space-y-[20px]">
          {/* Card 01: Your experience */}
          <section
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              handleFileSelect(e.dataTransfer.files?.[0]);
            }}
            className="rounded-[14px] border p-[24px] transition-colors"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: dragActive ? "var(--accent-lime)" : "var(--border-default)",
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />

            <div className="flex flex-wrap items-center justify-between gap-3 mb-[16px]">
              <div className="flex items-baseline gap-[16px]">
                <span
                  className="text-[11px] font-semibold tabular-nums"
                  style={{ color: "var(--text-secondary)" }}
                >
                  01
                </span>
                <h2
                  className="text-[19px] font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  Your experience
                </h2>
              </div>

              <div className="flex flex-wrap items-center gap-[8px]">
                {cvDoc ? (
                  <span
                    className="h-[28px] px-[10px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                    style={{
                      backgroundColor: "var(--surface-success)",
                      color: "var(--text-success)",
                    }}
                  >
                    Text extracted
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={handleLoadSample}
                    className="h-[28px] px-[10px] rounded-[6px] text-[11px] font-medium cursor-pointer"
                    style={{
                      backgroundColor: "var(--surface-subtle)",
                      color: "var(--text-primary)",
                    }}
                  >
                    Load sample CV
                  </button>
                )}
              </div>
            </div>

            {cvDoc ? (
              <div
                className="rounded-[9px] border px-[16px] py-[16px] flex items-center justify-between gap-4 mb-[20px]"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  borderColor: "var(--border-default)",
                }}
              >
                <div className="flex items-center gap-[16px] min-w-0">
                  <div
                    className="w-[42px] h-[46px] rounded-[6px] border flex items-center justify-center shrink-0"
                    style={{
                      backgroundColor: "var(--surface-card)",
                      borderColor: "var(--border-default)",
                    }}
                  >
                    <span
                      className="text-[10px] font-bold"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {cvDoc.file_type}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p
                      className="text-[14px] font-medium truncate"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {cvDoc.filename}
                    </p>
                    <p
                      className="text-[11px] font-normal mt-[3px]"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {formatFileSize(cvDoc.file_size_bytes)} &nbsp;·&nbsp; {cvDoc.page_count}{" "}
                      {cvDoc.page_count === 1 ? "page" : "pages"} &nbsp;·&nbsp; Ready to use
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="text-[12px] font-medium shrink-0 px-[10px] py-[6px] rounded-[6px] hover:opacity-80 cursor-pointer"
                  style={{ color: "var(--text-primary)" }}
                >
                  {uploading ? "Reading…" : "Replace"}
                </button>
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="rounded-[9px] border border-dashed px-[20px] py-[26px] text-center cursor-pointer mb-[18px] transition-colors"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  borderColor: "var(--border-default)",
                }}
              >
                <p className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
                  {uploading ? "Extracting your CV..." : "Drop your CV here, or click to upload"}
                </p>
                <p className="text-[11px] mt-[4px]" style={{ color: "var(--text-secondary)" }}>
                  PDF, DOCX, or PNG/JPG · Up to 10 MB · Auto-detects skills, projects & target role
                </p>
              </div>
            )}

            {uploadError && (
              <p className="text-[12px] mb-[12px]" style={{ color: "var(--text-warning)" }}>
                {uploadError}
              </p>
            )}

            {profile && (
              <>
                <p
                  className="text-[10px] font-semibold tracking-[0.04em] uppercase mb-[10px]"
                  style={{ color: "var(--text-secondary)" }}
                >
                  YOUR PROFILE AT A GLANCE
                </p>

                <div className="flex flex-wrap gap-[9px] mb-[14px]">
                  {[
                    profile.experience_level,
                    profile.years_experience,
                    profile.location,
                    ...profile.primary_skills.slice(0, 6),
                  ]
                    .filter((item): item is string => Boolean(item))
                    .filter((item, idx, arr) => arr.indexOf(item) === idx)
                    .map((chip) => (
                      <span
                        key={chip}
                        className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                        style={{
                          backgroundColor: "var(--surface-subtle)",
                          color: "var(--text-primary)",
                        }}
                      >
                        {chip}
                      </span>
                    ))}
                </div>

                <p className="text-[11px] font-normal" style={{ color: "var(--text-secondary)" }}>
                  {profile.projects_summary_line}
                </p>
              </>
            )}
          </section>

          {/* Card 02: Your next opportunity */}
          <section
            className="rounded-[14px] border p-[24px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <div className="flex items-center justify-between gap-3 mb-[18px]">
              <div className="flex items-baseline gap-[16px]">
                <span
                  className="text-[11px] font-semibold tabular-nums"
                  style={{ color: "var(--text-secondary)" }}
                >
                  02
                </span>
                <h2
                  className="text-[19px] font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  Your next opportunity
                </h2>
              </div>

              {research && (
                <button
                  type="button"
                  onClick={() => setShowResearchDrawer((v) => !v)}
                  className="h-[28px] px-[10px] rounded-[6px] text-[11px] font-medium inline-flex items-center gap-[6px] cursor-pointer transition-opacity hover:opacity-90"
                  style={{
                    backgroundColor: "var(--surface-category)",
                    color: "var(--text-category)",
                  }}
                >
                  <span>{research.archetype_short_label}</span>
                  <span>{showResearchDrawer ? "▴" : "▾"}</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-[20px] mb-[18px]">
              <div>
                <label
                  htmlFor="company-input"
                  className="block text-[12px] font-medium mb-[8px]"
                  style={{ color: "var(--text-primary)" }}
                >
                  Company
                </label>
                <input
                  id="company-input"
                  list="rehearse-companies"
                  value={companyName}
                  onChange={(e) => onCompanyNameChange(e.target.value)}
                  placeholder="e.g. Gendac, iStore, Electrum, KION, Stripe..."
                  className="w-full h-[46px] rounded-[7px] border px-[14px] text-[14px] focus:outline-none"
                  style={{
                    backgroundColor: "var(--surface-card)",
                    borderColor: "var(--border-default)",
                    color: "var(--text-primary)",
                  }}
                />
                <datalist id="rehearse-companies">
                  {knownCompanies.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.archetype_label}
                    </option>
                  ))}
                </datalist>
              </div>

              <div>
                <label
                  htmlFor="role-input"
                  className="block text-[12px] font-medium mb-[8px]"
                  style={{ color: "var(--text-primary)" }}
                >
                  Target role
                </label>
                <input
                  id="role-input"
                  list="rehearse-roles"
                  value={targetRole}
                  onChange={(e) => onTargetRoleChange(e.target.value)}
                  placeholder="e.g. Backend Engineer"
                  className="w-full h-[46px] rounded-[7px] border px-[14px] text-[14px] focus:outline-none"
                  style={{
                    backgroundColor: "var(--surface-card)",
                    borderColor: "var(--border-default)",
                    color: "var(--text-primary)",
                  }}
                />
                <datalist id="rehearse-roles">
                  {ROLE_SUGGESTIONS.map((r) => (
                    <option key={r} value={r} />
                  ))}
                </datalist>
              </div>
            </div>

            {/* Researched Company Interview Intelligence Panel (expandable so main UI stays clean!) */}
            {research && showResearchDrawer && (
              <div
                className="rounded-[10px] border p-[16px] mb-[18px] space-y-[12px]"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  borderColor: "var(--border-default)",
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p
                      className="text-[10px] font-semibold uppercase tracking-[0.05em]"
                      style={{ color: "var(--text-list-index)" }}
                    >
                      RESEARCHED INTERVIEW PROCESS · {research.company_name.toUpperCase()}
                    </p>
                    <p
                      className="text-[12px] mt-[4px] leading-relaxed"
                      style={{ color: "var(--text-body)" }}
                    >
                      {research.deduplication_note}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-[8px]">
                  {research.rounds.map((rd) => (
                    <div
                      key={rd.stage}
                      className="rounded-[7px] border px-[11px] py-[9px]"
                      style={{
                        backgroundColor: "var(--surface-card)",
                        borderColor: "var(--border-default)",
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-semibold" style={{ color: "var(--text-primary)" }}>
                          {rd.stage} · {rd.name}
                        </span>
                        <span className="text-[10px] whitespace-nowrap shrink-0" style={{ color: "var(--text-secondary)" }}>
                          {rd.duration}
                        </span>
                      </div>
                      <p className="text-[10px] mt-[3px] leading-snug" style={{ color: "var(--text-secondary)" }}>
                        {rd.format}
                      </p>
                    </div>
                  ))}
                </div>

                {research.company_nuances.length > 0 && (
                  <div className="space-y-[4px]">
                    {research.company_nuances.slice(0, 2).map((n, i) => (
                      <p key={i} className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                        • {n}
                      </p>
                    ))}
                  </div>
                )}

                {research.coding_and_leetcode_patterns && research.coding_and_leetcode_patterns.length > 0 && (
                  <div>
                    <p
                      className="text-[10px] font-semibold uppercase tracking-[0.05em] mb-[4px]"
                      style={{ color: "var(--text-list-index)" }}
                    >
                      CODING / LEETCODE & TECHNICAL FOCUS
                    </p>
                    <div className="space-y-[2px]">
                      {research.coding_and_leetcode_patterns.slice(0, 3).map((pat, idx) => (
                        <p key={idx} className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                          • {pat}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {research.company_grading_rubric && research.company_grading_rubric.length > 0 && (
                  <div>
                    <p
                      className="text-[10px] font-semibold uppercase tracking-[0.05em] mb-[4px]"
                      style={{ color: "var(--text-list-index)" }}
                    >
                      HOW {research.company_name.toUpperCase()} GRADES ANSWERS
                    </p>
                    <div className="space-y-[2px]">
                      {research.company_grading_rubric.slice(0, 2).map((rub, idx) => (
                        <p key={idx} className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                          • {rub}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <label
                htmlFor="jd-input"
                className="block text-[12px] font-medium mb-[8px]"
                style={{ color: "var(--text-primary)" }}
              >
                Job description
              </label>
              <textarea
                id="jd-input"
                value={jobDescription}
                onChange={(e) => {
                  userEditedJdKeyRef.current = currentPairKey;
                  onJobDescriptionChange(e.target.value);
                }}
                rows={5}
                placeholder="Paste or review the researched role responsibilities and requirements..."
                className="w-full min-h-[126px] rounded-[7px] border px-[14px] py-[12px] text-[13px] leading-[1.5] resize-y focus:outline-none"
                style={{
                  backgroundColor: "var(--surface-card)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-input)",
                }}
              />
            </div>

            <div className="flex items-center justify-between mt-[10px] mb-[12px]">
              <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                {jobDescription.length.toLocaleString()} characters
              </p>
              {researchLoading ? (
                <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                  Researching {companyName} interview loop…
                </p>
              ) : research ? (
                <button
                  type="button"
                  onClick={() => setShowResearchDrawer((v) => !v)}
                  className="text-[10px] font-medium cursor-pointer hover:underline"
                  style={{ color: "var(--text-list-index)" }}
                >
                  {research.rounds.length} real rounds mapped · Shared with{" "}
                  {research.shared_companies.slice(0, 3).join(", ")} →
                </button>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-[9px]">
              {jdSignals.map((sig) => (
                <span
                  key={sig}
                  className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                  style={{
                    backgroundColor: "var(--surface-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  {sig}
                </span>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column */}
        <div className="space-y-[20px]">
          {/* Deep Forest Feature Card */}
          <section
            className="rounded-[14px] p-[24px] flex flex-col justify-between min-h-[375px]"
            style={{ backgroundColor: "var(--surface-feature)" }}
          >
            <div>
              <span
                className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center tracking-[0.02em]"
                style={{
                  backgroundColor: "var(--surface-feature-control)",
                  color: "var(--text-feature-tag)",
                }}
              >
                BUILT AROUND YOU
              </span>

              <div
                className="text-[28px] font-semibold leading-[1.32] tracking-[-0.015em] mt-[24px]"
                style={{ color: "var(--text-feature-heading)" }}
              >
                <p className="m-0">Not a question bank.</p>
                <p className="m-0">Your next interview.</p>
              </div>

              <p
                className="text-[13px] font-normal leading-[1.5] mt-[16px]"
                style={{ color: "var(--text-feature-muted)" }}
              >
                A balanced session grounded in your CV, {companyName || "the company"}’s real rounds, and the role you want.
              </p>
            </div>

            <div className="mt-[28px]">
              <div className="grid grid-cols-2 gap-[16px] mb-[22px]">
                <div>
                  <div className="flex items-center gap-[8px]">
                    <span
                      className="text-[25px] font-semibold leading-none tabular-nums"
                      style={{ color: "var(--accent-lime)" }}
                    >
                      {questionCount}
                    </span>
                    <div className="flex gap-[3px]">
                      {[5, 6, 8].map((n) => (
                        <button
                          key={n}
                          type="button"
                          onClick={() => onQuestionCountChange(n)}
                          className="w-[20px] h-[20px] rounded-[4px] text-[10px] font-medium cursor-pointer transition-opacity"
                          style={{
                            backgroundColor:
                              questionCount === n
                                ? "var(--accent-lime)"
                                : "var(--surface-feature-control)",
                            color:
                              questionCount === n
                                ? "var(--text-on-lime)"
                                : "var(--text-feature-muted)",
                          }}
                          title={`${n} questions`}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                  </div>
                  <p
                    className="text-[11px] mt-[8px]"
                    style={{ color: "var(--text-feature-muted)" }}
                  >
                    tailored questions
                  </p>
                </div>

                <div>
                  <p
                    className="text-[25px] font-semibold leading-none tabular-nums"
                    style={{ color: "var(--accent-lime)" }}
                  >
                    ~{estMinutes} min
                  </p>
                  <p
                    className="text-[11px] mt-[8px]"
                    style={{ color: "var(--text-feature-muted)" }}
                  >
                    at your own pace
                  </p>
                </div>
              </div>

              {/* Subtle round focus selector */}
              <div className="flex flex-wrap gap-[6px] mb-[14px]">
                {ROUND_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => onRoundFocusChange(opt.id)}
                    className="h-[24px] px-[8px] rounded-[5px] text-[10px] font-medium cursor-pointer transition-colors"
                    style={{
                      backgroundColor:
                        roundFocus === opt.id
                          ? "var(--accent-lime)"
                          : "var(--surface-feature-control)",
                      color:
                        roundFocus === opt.id
                          ? "var(--text-on-lime)"
                          : "var(--text-feature-caption)",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              <p
                className="text-[10px] font-normal"
                style={{ color: "var(--text-feature-caption)" }}
              >
                Technical depth &nbsp;·&nbsp; Behavioral &nbsp;·&nbsp; Project deep dives
              </p>
            </div>
          </section>

          {/* What we'll explore */}
          <section
            className="rounded-[14px] border p-[24px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <h3
              className="text-[17px] font-semibold mb-[22px]"
              style={{ color: "var(--text-primary)" }}
            >
              What we’ll explore
            </h3>

            <div className="space-y-[20px]">
              {exploreItems.map((item) => (
                <div key={item.index} className="flex items-start gap-[18px]">
                  <span
                    className="text-[11px] font-semibold tabular-nums mt-[2px]"
                    style={{ color: "var(--text-list-index)" }}
                  >
                    {item.index}
                  </span>
                  <div>
                    <p
                      className="text-[13px] font-medium leading-snug"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {item.title}
                    </p>
                    <p
                      className="text-[11px] font-normal mt-[4px] leading-relaxed"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* Error feedback */}
      {error && (
        <div
          className="mt-[18px] rounded-[9px] px-[16px] py-[12px] text-[12px]"
          style={{
            backgroundColor: "var(--surface-warning)",
            color: "var(--text-warning)",
          }}
        >
          {error}
        </div>
      )}

      {/* Bottom Privacy & Primary CTA Bar */}
      <div className="mt-[22px] flex flex-col sm:flex-row sm:items-center justify-between gap-[16px]">
        <div>
          <p className="text-[11px] font-normal" style={{ color: "var(--text-secondary)" }}>
            Your CV stays private. You control when it’s deleted.
          </p>
          <p className="text-[10px] font-normal mt-[6px]" style={{ color: "var(--text-tertiary)" }}>
            PDF, DOCX, or PNG/JPG &nbsp;·&nbsp; Up to 10 MB &nbsp;·&nbsp; No audio recorded yet
          </p>
        </div>

        <button
          type="button"
          onClick={onGenerateInterview}
          disabled={generating || !companyName.trim() || !targetRole.trim()}
          className="w-full sm:w-[304px] h-[48px] rounded-[8px] px-[24px] text-[14px] font-semibold flex items-center justify-center gap-[14px] transition-opacity hover:opacity-95 disabled:opacity-55 cursor-pointer"
          style={{
            backgroundColor: "var(--accent-lime)",
            color: "var(--text-on-lime)",
          }}
        >
          <span>{generating ? "Building your loop…" : "Generate my interview"}</span>
          <span>→</span>
        </button>
      </div>
    </div>
  );
}
