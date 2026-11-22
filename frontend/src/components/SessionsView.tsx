"use client";

import React from "react";
import type { InterviewSession } from "@/types/rehearse";

interface SessionsViewProps {
  sessions: InterviewSession[];
  onResumeSession: (session: InterviewSession) => void;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onStartNew: () => void;
}

export default function SessionsView({
  sessions,
  onResumeSession,
  onDeleteSession,
  onStartNew,
}: SessionsViewProps) {
  return (
    <div className="w-full max-w-[1128px] mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-[16px] mb-[26px]">
        <div>
          <h1
            className="text-[32px] font-semibold leading-[1.3] tracking-[-0.02em]"
            style={{ color: "var(--text-primary)" }}
          >
            My sessions.
          </h1>
          <p className="text-[14px] mt-[8px]" style={{ color: "var(--text-secondary)" }}>
            Revisit transcripts, rubric scores, and rewrites from every mock interview.
          </p>
        </div>

        <button
          type="button"
          onClick={onStartNew}
          className="h-[44px] px-[22px] rounded-[8px] text-[13px] font-semibold shrink-0 cursor-pointer"
          style={{
            backgroundColor: "var(--accent-lime)",
            color: "var(--text-on-lime)",
          }}
        >
          Start new interview &nbsp;→
        </button>
      </div>

      {sessions.length === 0 ? (
        <div
          className="rounded-[14px] border p-[40px] text-center"
          style={{
            backgroundColor: "var(--surface-card)",
            borderColor: "var(--border-default)",
          }}
        >
          <p className="text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
            No practice sessions yet
          </p>
          <p className="text-[13px] mt-[8px] mb-[20px]" style={{ color: "var(--text-secondary)" }}>
            Upload your CV and paste a target tech role to generate your first tailored mock interview.
          </p>
          <button
            type="button"
            onClick={onStartNew}
            className="h-[40px] px-[20px] rounded-[8px] text-[12px] font-semibold cursor-pointer"
            style={{
              backgroundColor: "var(--accent-lime)",
              color: "var(--text-on-lime)",
            }}
          >
            Set up an interview →
          </button>
        </div>
      ) : (
        <div className="space-y-[14px]">
          {sessions.map((s) => {
            const done = s.questions.filter((q) => q.status === "completed").length;
            const total = s.questions.length;
            const dateStr = new Date(s.updated_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <div
                key={s.id}
                className="rounded-[14px] border p-[22px] flex flex-col sm:flex-row sm:items-center justify-between gap-[16px]"
                style={{
                  backgroundColor: "var(--surface-card)",
                  borderColor: "var(--border-default)",
                }}
              >
                <div className="space-y-[6px]">
                  <div className="flex flex-wrap items-center gap-[8px]">
                    <span
                      className="h-[24px] px-[9px] rounded-[5px] text-[10px] font-medium inline-flex items-center"
                      style={{
                        backgroundColor: "var(--surface-category)",
                        color: "var(--text-category)",
                      }}
                    >
                      {s.company_research?.archetype_short_label || "Tech Loop"}
                    </span>
                    <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                      {dateStr}
                    </span>
                  </div>
                  <h2 className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
                    {s.target_role} at {s.company_name}
                  </h2>
                  <p className="text-[12px]" style={{ color: "var(--text-secondary)" }}>
                    {done} of {total} questions evaluated
                    {s.jd_signals.length > 0 ? `  ·  ${s.jd_signals.slice(0, 3).join(", ")}` : ""}
                  </p>
                </div>

                <div className="flex items-center gap-[14px]">
                  {s.overall_score !== null && (
                    <div className="text-right pr-[8px]">
                      <p
                        className="text-[24px] font-semibold leading-none tabular-nums"
                        style={{ color: "var(--text-success)" }}
                      >
                        {s.overall_score}
                      </p>
                      <p className="text-[10px] mt-[3px]" style={{ color: "var(--text-secondary)" }}>
                        avg score
                      </p>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => onResumeSession(s)}
                    className="h-[38px] px-[18px] rounded-[7px] text-[12px] font-semibold cursor-pointer"
                    style={{
                      backgroundColor: "var(--accent-lime)",
                      color: "var(--text-on-lime)",
                    }}
                  >
                    {done === total && total > 0 ? "Review results" : "Continue"} →
                  </button>

                  <button
                    type="button"
                    onClick={() => onDeleteSession(s.id)}
                    className="h-[38px] px-[12px] rounded-[7px] border text-[11px] font-medium cursor-pointer hover:opacity-80"
                    style={{
                      backgroundColor: "var(--surface-subtle)",
                      borderColor: "var(--border-default)",
                      color: "var(--text-secondary)",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
