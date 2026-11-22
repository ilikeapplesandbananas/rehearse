"use client";

import React, { useState } from "react";
import type { ArchetypeOverview, OverviewStats } from "@/types/rehearse";

interface OverviewViewProps {
  stats: OverviewStats | null;
  archetypes: ArchetypeOverview[];
  onStartNewInterview: (presetCompany?: string) => void;
  onOpenSession: (sessionId: string) => void;
}

export default function OverviewView({
  stats,
  archetypes,
  onStartNewInterview,
  onOpenSession,
}: OverviewViewProps) {
  const [expandedArch, setExpandedArch] = useState<string | null>(
    archetypes[0]?.id || null
  );

  const avg = stats?.average_scores || {
    communication: 0,
    technical_depth: 0,
    structure: 0,
    confidence: 0,
  };

  return (
    <div className="w-full max-w-[1128px] mx-auto space-y-[24px]">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-[16px]">
        <div>
          <h1
            className="text-[32px] font-semibold leading-[1.3] tracking-[-0.02em]"
            style={{ color: "var(--text-primary)" }}
          >
            Your interview readiness.
          </h1>
          <p
            className="text-[14px] mt-[8px]"
            style={{ color: "var(--text-secondary)" }}
          >
            Track score momentum and explore real, deduplicated tech company interview loops.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onStartNewInterview()}
          className="h-[44px] px-[22px] rounded-[8px] text-[13px] font-semibold shrink-0 cursor-pointer"
          style={{
            backgroundColor: "var(--accent-lime)",
            color: "var(--text-on-lime)",
          }}
        >
          New practice session &nbsp;→
        </button>
      </div>

      {/* Metrics Banner */}
      <section
        className="rounded-[14px] px-[26px] py-[22px] grid grid-cols-1 lg:grid-cols-[208px_1fr] gap-[24px] items-center"
        style={{ backgroundColor: "var(--surface-feature)" }}
      >
        <div
          className="lg:border-r lg:pr-[24px]"
          style={{ borderColor: "var(--border-feature)" }}
        >
          <div className="flex items-baseline gap-[8px]">
            <span
              className="text-[48px] font-semibold leading-none tabular-nums"
              style={{ color: "var(--accent-lime)" }}
            >
              {stats?.average_overall ?? "--"}
            </span>
            {stats?.average_overall !== null && stats?.average_overall !== undefined && (
              <span className="text-[13px]" style={{ color: "var(--text-score-unit)" }}>
                / 100
              </span>
            )}
          </div>
          <p className="text-[11px] mt-[12px]" style={{ color: "var(--text-score-caption)" }}>
            Average score ({stats?.total_answers_evaluated || 0}{" "}
            {(stats?.total_answers_evaluated || 0) === 1 ? "answer" : "answers"})
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-[24px]">
          {[
            { label: "Communication", val: avg.communication },
            { label: "Technical depth", val: avg.technical_depth },
            { label: "Structure", val: avg.structure },
            { label: "Confidence", val: avg.confidence },
          ].map((col) => (
            <div key={col.label}>
              <p className="text-[12px] font-medium" style={{ color: "var(--text-score-label)" }}>
                {col.label}
              </p>
              <p
                className="text-[28px] font-semibold mt-[4px] tabular-nums"
                style={{ color: "var(--text-score-value)" }}
              >
                {col.val > 0 ? col.val : "--"}
              </p>
              <div
                className="w-full h-[3px] rounded-[2px] mt-[8px] overflow-hidden"
                style={{ backgroundColor: "var(--indicator-score-track)" }}
              >
                <div
                  className="h-full rounded-[2px]"
                  style={{
                    width: `${col.val}%`,
                    backgroundColor: "var(--accent-lime)",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Deduplicated Tech Interview Archetypes Explorer */}
      <section
        className="rounded-[14px] border p-[24px]"
        style={{
          backgroundColor: "var(--surface-card)",
          borderColor: "var(--border-default)",
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-[18px]">
          <div>
            <p
              className="text-[10px] font-semibold uppercase tracking-[0.05em]"
              style={{ color: "var(--text-list-index)" }}
            >
              RESEARCHED FROM REDDIT, GLASSDOOR &amp; BLIND · TECH ROLES
            </p>
            <h2 className="text-[19px] font-semibold mt-[4px]" style={{ color: "var(--text-primary)" }}>
              {archetypes.length} Deduplicated Tech Interview Archetypes
            </h2>
          </div>
          <span
            className="h-[26px] px-[10px] rounded-[6px] text-[11px] font-medium inline-flex items-center self-start"
            style={{
              backgroundColor: "var(--surface-subtle)",
              color: "var(--text-secondary)",
            }}
          >
            Companies sharing a loop reuse core prep
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-[14px]">
          {archetypes.map((arch, idx) => {
            const isOpen = expandedArch === arch.id;
            return (
              <div
                key={arch.id}
                className="rounded-[10px] border p-[16px] flex flex-col justify-between"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  borderColor: isOpen ? "var(--indicator-progress)" : "var(--border-default)",
                }}
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span
                        className="text-[10px] font-semibold tabular-nums"
                        style={{ color: "var(--text-list-index)" }}
                      >
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                      <h3
                        className="text-[14px] font-semibold mt-[2px]"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {arch.name}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setExpandedArch(isOpen ? null : arch.id)}
                      className="text-[11px] font-medium cursor-pointer shrink-0"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {isOpen ? "Hide rounds ▴" : "View rounds ▾"}
                    </button>
                  </div>

                  <p
                    className="text-[12px] leading-relaxed mt-[8px]"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {arch.summary}
                  </p>

                  <div className="flex flex-wrap gap-[6px] mt-[12px]">
                    {arch.shared_companies.slice(0, 7).map((co) => (
                      <button
                        key={co}
                        type="button"
                        onClick={() => onStartNewInterview(co)}
                        className="px-[8px] py-[4px] rounded-[5px] text-[10px] font-medium cursor-pointer transition-opacity hover:opacity-80"
                        style={{
                          backgroundColor: "var(--surface-card)",
                          color: "var(--text-primary)",
                        }}
                        title={`Practice ${co} interview`}
                      >
                        {co}
                      </button>
                    ))}
                  </div>

                  {isOpen && (
                    <div className="mt-[14px] pt-[12px] border-t space-y-[8px]" style={{ borderColor: "var(--border-default)" }}>
                      {arch.standard_rounds.map((r) => (
                        <div key={r.stage} className="text-[11px]">
                          <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                            {r.stage}. {r.name}
                          </span>{" "}
                          <span style={{ color: "var(--text-tertiary)" }}>({r.duration})</span>
                          <p className="mt-[2px]" style={{ color: "var(--text-secondary)" }}>
                            {r.format}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-[14px] pt-[10px] border-t flex items-center justify-between" style={{ borderColor: "var(--border-default)" }}>
                  <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                    {arch.standard_rounds.length} typical rounds
                  </span>
                  <button
                    type="button"
                    onClick={() => onStartNewInterview(arch.shared_companies[0])}
                    className="text-[11px] font-semibold cursor-pointer hover:underline"
                    style={{ color: "var(--text-success)" }}
                  >
                    Practice {arch.shared_companies[0]} loop →
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Recent sessions */}
      {stats && stats.recent_sessions.length > 0 && (
        <section
          className="rounded-[14px] border p-[24px]"
          style={{
            backgroundColor: "var(--surface-card)",
            borderColor: "var(--border-default)",
          }}
        >
          <h2 className="text-[18px] font-semibold mb-[14px]" style={{ color: "var(--text-primary)" }}>
            Recent practice sessions
          </h2>
          <div className="space-y-[10px]">
            {stats.recent_sessions.map((s) => (
              <div
                key={s.id}
                className="rounded-[9px] border px-[16px] py-[13px] flex flex-wrap items-center justify-between gap-3"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  borderColor: "var(--border-default)",
                }}
              >
                <div>
                  <p className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
                    {s.target_role} at {s.company_name}
                  </p>
                  <p className="text-[11px] mt-[3px]" style={{ color: "var(--text-secondary)" }}>
                    {s.completed_questions} of {s.total_questions} questions answered
                  </p>
                </div>

                <div className="flex items-center gap-[14px]">
                  {s.overall_score !== null && (
                    <span
                      className="text-[13px] font-semibold tabular-nums"
                      style={{ color: "var(--text-success)" }}
                    >
                      {s.overall_score} / 100
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => onOpenSession(s.id)}
                    className="h-[32px] px-[14px] rounded-[6px] text-[11px] font-medium cursor-pointer"
                    style={{
                      backgroundColor: "var(--surface-card)",
                      color: "var(--text-primary)",
                    }}
                  >
                    {s.status === "completed" ? "Review" : "Resume"} →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
