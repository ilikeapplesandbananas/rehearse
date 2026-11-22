"use client";

import React, { useState } from "react";
import type { InterviewSession, SessionQuestion } from "@/types/rehearse";

interface AnswerReviewScreenProps {
  session: InterviewSession;
  questionIndex: number;
  onRetryQuestion: () => void;
  onContinueNext: () => void;
  onOpenStudyPlan: () => void;
}

export default function AnswerReviewScreen({
  session,
  questionIndex,
  onRetryQuestion,
  onContinueNext,
  onOpenStudyPlan,
}: AnswerReviewScreenProps) {
  const [showTranscriptModal, setShowTranscriptModal] = useState(false);

  const question: SessionQuestion | undefined = session.questions[questionIndex];
  const attempt = question?.latest_attempt;
  if (!question || !attempt) return null;

  const { evaluation, delivery_metrics: dm } = attempt;
  const { scores } = evaluation;
  const qNum = String(questionIndex + 1).padStart(2, "0");
  const hasNext = questionIndex + 1 < session.questions.length;
  const nextNum = String(questionIndex + 2).padStart(2, "0");

  const rubricCols = [
    {
      label: "Communication",
      value: scores.communication,
      note: scores.communication_note,
    },
    {
      label: "Technical depth",
      value: scores.technical_depth,
      note: scores.technical_depth_note,
    },
    {
      label: "Structure",
      value: scores.structure,
      note: scores.structure_note,
    },
    {
      label: "Confidence",
      value: scores.confidence,
      note: scores.confidence_note,
    },
  ];

  const gaps =
    evaluation.gaps && evaluation.gaps.length > 0
      ? evaluation.gaps
      : [
          { index: "01", title: "What went wrong", detail: evaluation.what_went_wrong },
          { index: "02", title: "What was missing", detail: evaluation.what_was_missing },
        ];

  const sampleParagraphs =
    evaluation.sample_paragraphs && evaluation.sample_paragraphs.length > 0
      ? evaluation.sample_paragraphs
      : evaluation.sample_strong_answer
          .split(/\n\n+/)
          .map((p) => p.trim())
          .filter(Boolean);

  const signalStatusColor = (status: "good" | "warn" | "neutral") =>
    status === "good"
      ? "var(--text-steady)"
      : status === "warn"
      ? "var(--text-caution)"
      : "var(--text-secondary)";

  return (
    <div className="w-full max-w-[1128px] mx-auto">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-[16px] mb-[26px]">
        <div>
          <h1
            className="text-[32px] font-semibold leading-[1.3] tracking-[-0.02em]"
            style={{ color: "var(--text-primary)" }}
          >
            {evaluation.headline}
          </h1>
          <p
            className="text-[14px] font-normal mt-[8px]"
            style={{ color: "var(--text-secondary)" }}
          >
            Question {qNum} review &nbsp;/&nbsp; {session.target_role} at {session.company_name}
          </p>
        </div>

        <button
          type="button"
          onClick={onRetryQuestion}
          className="h-[38px] px-[22px] rounded-[7px] border text-[12px] font-medium shrink-0 self-start transition-opacity hover:opacity-85 cursor-pointer"
          style={{
            backgroundColor: "var(--surface-card)",
            borderColor: "var(--border-default)",
            color: "var(--text-primary)",
          }}
        >
          ↻ &nbsp;&nbsp;Try this again
        </button>
      </div>

      {/* Answer Scores Banner (Full-width Deep Forest #203326) */}
      <section
        className="rounded-[14px] px-[26px] py-[22px] mb-[20px] grid grid-cols-1 lg:grid-cols-[208px_1fr] gap-[24px] items-center"
        style={{ backgroundColor: "var(--surface-feature)" }}
      >
        <div
          className="lg:border-r lg:pr-[24px]"
          style={{ borderColor: "var(--border-feature)" }}
        >
          <div className="flex items-baseline gap-[10px]">
            <span
              className="text-[54px] font-semibold leading-[1.1] tabular-nums"
              style={{ color: "var(--accent-lime)" }}
            >
              {scores.overall}
            </span>
            <span
              className="text-[13px] font-normal"
              style={{ color: "var(--text-score-unit)" }}
            >
              / 100
            </span>
          </div>
          <p
            className="text-[11px] font-normal mt-[14px]"
            style={{ color: "var(--text-score-caption)" }}
          >
            Overall answer score
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-[24px]">
          {rubricCols.map((col) => (
            <div key={col.label}>
              <p
                className="text-[12px] font-medium"
                style={{ color: "var(--text-score-label)" }}
              >
                {col.label}
              </p>
              <p
                className="text-[32px] font-semibold leading-[1.25] mt-[4px] tabular-nums"
                style={{ color: "var(--text-score-value)" }}
              >
                {col.value}
              </p>
              <div
                className="w-full h-[3px] rounded-[2px] mt-[8px] overflow-hidden"
                style={{ backgroundColor: "var(--indicator-score-track)" }}
              >
                <div
                  className="h-full rounded-[2px] transition-all duration-500"
                  style={{
                    width: `${Math.min(100, Math.max(4, col.value))}%`,
                    backgroundColor: "var(--accent-lime)",
                  }}
                />
              </div>
              <p
                className="text-[10px] font-normal mt-[9px]"
                style={{ color: "var(--text-score-label)" }}
              >
                {col.note}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Reviewed Question Strip */}
      <section
        className="rounded-[10px] border px-[16px] py-[16px] mb-[20px] flex flex-col sm:flex-row sm:items-center justify-between gap-[14px]"
        style={{
          backgroundColor: "var(--surface-card)",
          borderColor: "var(--border-default)",
        }}
      >
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-[18px] min-w-0">
          <span
            className="h-[28px] px-[12px] rounded-[6px] text-[11px] font-medium inline-flex items-center shrink-0 uppercase tracking-[0.02em]"
            style={{
              backgroundColor: "var(--surface-subtle)",
              color: "var(--text-primary)",
            }}
          >
            {qNum} &nbsp;/&nbsp; {question.category}
          </span>
          <p
            className="text-[14px] font-medium truncate"
            style={{ color: "var(--text-primary)" }}
          >
            {question.question_text}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowTranscriptModal(true)}
          className="text-[11px] font-medium shrink-0 cursor-pointer hover:underline self-end sm:self-center"
          style={{ color: "var(--text-secondary)" }}
        >
          View transcript &nbsp;↗
        </button>
      </section>

      {/* 2-Column Feedback Grid matching Figma 704 / 400 ratio */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,704fr)_minmax(0,400fr)] gap-[24px] items-start">
        {/* Left Column */}
        <div className="space-y-[20px]">
          {/* What to work on */}
          <section
            className="rounded-[14px] border p-[24px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <div className="flex items-center justify-between gap-3 mb-[20px]">
              <h2
                className="text-[18px] font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                What to work on
              </h2>
              <span
                className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                style={{
                  backgroundColor: "var(--surface-warning)",
                  color: "var(--text-warning)",
                }}
              >
                {gaps.length} key {gaps.length === 1 ? "gap" : "gaps"}
              </span>
            </div>

            <div className="space-y-[18px] mb-[22px]">
              {gaps.map((g) => (
                <div key={g.index}>
                  <p
                    className="text-[12px] font-semibold"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {g.index} &nbsp;&nbsp;{g.title}
                  </p>
                  <p
                    className="text-[12px] font-normal mt-[6px] leading-[1.5]"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {g.detail}
                  </p>
                </div>
              ))}
            </div>

            {/* THE FIX strip */}
            <div
              className="rounded-[7px] px-[14px] py-[13px] flex flex-col sm:flex-row sm:items-center gap-[10px] sm:gap-[24px]"
              style={{ backgroundColor: "var(--surface-fix)" }}
            >
              <span
                className="text-[9px] font-semibold tracking-[0.06em] uppercase shrink-0"
                style={{ color: "var(--text-fix-label)" }}
              >
                THE FIX
              </span>
              <p
                className="text-[12px] font-medium leading-snug"
                style={{ color: "var(--text-primary)" }}
              >
                {evaluation.fix_formula || evaluation.how_to_fix}
              </p>
            </div>
          </section>

          {/* A stronger way to answer */}
          <section
            className="rounded-[14px] border p-[24px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <div className="flex items-center justify-between gap-3 mb-[20px]">
              <h2
                className="text-[18px] font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                A stronger way to answer
              </h2>
              <span
                className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center tracking-[0.02em]"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  color: "var(--text-primary)",
                }}
              >
                EXAMPLE REWRITE
              </span>
            </div>

            <div className="space-y-[16px]">
              {sampleParagraphs.map((para, idx) => (
                <p
                  key={idx}
                  className="text-[13px] font-normal leading-[1.6]"
                  style={{ color: "var(--text-body)" }}
                >
                  {para}
                </p>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column */}
        <div className="space-y-[20px]">
          {/* Beyond the transcript (Voice Delivery Signals) */}
          <section
            className="rounded-[14px] border p-[24px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <h2
              className="text-[18px] font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Beyond the transcript
            </h2>
            <p
              className="text-[11px] font-normal mt-[6px] mb-[22px]"
              style={{ color: "var(--text-secondary)" }}
            >
              Delivery signals from your {dm.duration_formatted} answer
            </p>

            <div className="space-y-[18px] mb-[26px]">
              <div className="grid grid-cols-[1.2fr_1fr_auto] items-center gap-3">
                <span className="text-[12px]" style={{ color: "var(--text-secondary)" }}>
                  Speaking pace
                </span>
                <span
                  className="text-[12px] font-semibold tabular-nums"
                  style={{ color: "var(--text-primary)" }}
                >
                  {dm.speaking_pace_wpm} WPM
                </span>
                <span
                  className="text-[10px] font-medium text-right"
                  style={{ color: signalStatusColor(dm.pace_status) }}
                >
                  {dm.pace_label}
                </span>
              </div>

              <div className="grid grid-cols-[1.2fr_1fr_auto] items-center gap-3">
                <span className="text-[12px]" style={{ color: "var(--text-secondary)" }}>
                  Filler words
                </span>
                <span
                  className="text-[12px] font-semibold tabular-nums"
                  style={{ color: "var(--text-primary)" }}
                >
                  {dm.filler_per_min} / min
                </span>
                <span
                  className="text-[10px] font-medium text-right"
                  style={{ color: signalStatusColor(dm.filler_status) }}
                >
                  {dm.filler_label}
                </span>
              </div>

              <div className="grid grid-cols-[1.2fr_1fr_auto] items-center gap-3">
                <span className="text-[12px]" style={{ color: "var(--text-secondary)" }}>
                  Longest pause
                </span>
                <span
                  className="text-[12px] font-semibold tabular-nums"
                  style={{ color: "var(--text-primary)" }}
                >
                  {dm.longest_pause_sec} sec
                </span>
                <span
                  className="text-[10px] font-medium text-right"
                  style={{ color: signalStatusColor(dm.pause_status) }}
                >
                  {dm.pause_label}
                </span>
              </div>
            </div>

            {dm.hedging_phrases.length > 0 && (
              <p className="text-[10px] mb-[12px]" style={{ color: "var(--text-caution)" }}>
                Hedging noted: “{dm.hedging_phrases.slice(0, 2).join("”, “")}”
              </p>
            )}

            <p className="text-[10px] font-normal" style={{ color: "var(--text-secondary)" }}>
              These are coaching signals, not a measure of ability.
            </p>
          </section>

          {/* Close the gaps (Personalized Study Plan) */}
          <section
            className="rounded-[14px] p-[24px]"
            style={{ backgroundColor: "var(--surface-advice)" }}
          >
            <h2
              className="text-[18px] font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Close the gaps
            </h2>
            <p
              className="text-[11px] font-normal mt-[6px] mb-[22px]"
              style={{ color: "var(--text-secondary)" }}
            >
              {evaluation.study_material.length === 1
                ? "One focused topic for your next attempt."
                : "Two focused topics for your next attempt."}
            </p>

            <div>
              {evaluation.study_material.slice(0, 3).map((item, idx) => (
                <div key={item.topic}>
                  {idx > 0 && (
                    <div
                      className="h-px my-[18px]"
                      style={{ backgroundColor: "var(--border-advice)" }}
                    />
                  )}
                  <div className="flex items-start gap-[16px]">
                    <span
                      className="text-[10px] font-semibold tabular-nums mt-[3px]"
                      style={{ color: "var(--text-advice-index)" }}
                    >
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <a
                        href={
                          item.resource_url ||
                          `https://www.google.com/search?q=${encodeURIComponent(
                            item.search_query_or_resource || item.topic
                          )}`
                        }
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[13px] font-semibold inline-flex items-center gap-[8px] hover:underline"
                        style={{ color: "var(--text-primary)" }}
                      >
                        <span>{item.topic}</span>
                        <span>↗</span>
                      </a>
                      {item.subtitle && (
                        <p
                          className="text-[11px] font-normal mt-[6px] leading-[1.45]"
                          style={{ color: "var(--text-advice)" }}
                        >
                          {item.subtitle}
                        </p>
                      )}
                      <p
                        className="text-[11px] font-normal mt-[3px] leading-[1.45]"
                        style={{ color: "var(--text-advice)" }}
                      >
                        {item.why}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* Footer CTA Bar */}
      <div className="mt-[22px] flex flex-col sm:flex-row sm:items-center justify-between gap-[16px]">
        <p className="text-[11px] font-normal" style={{ color: "var(--text-secondary)" }}>
          Your answer and feedback are saved to this session.
        </p>

        {hasNext ? (
          <button
            type="button"
            onClick={onContinueNext}
            className="w-full sm:w-[270px] h-[46px] rounded-[8px] px-[24px] text-[13px] font-semibold flex items-center justify-center gap-[12px] transition-opacity hover:opacity-95 cursor-pointer"
            style={{
              backgroundColor: "var(--accent-lime)",
              color: "var(--text-on-lime)",
            }}
          >
            <span>Continue to question {nextNum}</span>
            <span>→</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={onOpenStudyPlan}
            className="w-full sm:w-[270px] h-[46px] rounded-[8px] px-[24px] text-[13px] font-semibold flex items-center justify-center gap-[12px] transition-opacity hover:opacity-95 cursor-pointer"
            style={{
              backgroundColor: "var(--accent-lime)",
              color: "var(--text-on-lime)",
            }}
          >
            <span>Open full study plan</span>
            <span>→</span>
          </button>
        )}
      </div>

      {/* Verbatim Transcript & Delivery Telemetry Modal */}
      {showTranscriptModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-[2px]"
          onClick={() => setShowTranscriptModal(false)}
        >
          <div
            className="w-full max-w-[660px] max-h-[85vh] overflow-y-auto rounded-[14px] border p-[26px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4 mb-[18px]">
              <div>
                <p
                  className="text-[10px] font-semibold uppercase tracking-[0.05em]"
                  style={{ color: "var(--text-list-index)" }}
                >
                  VERBATIM TRANSCRIPT · {attempt.stt_provider.toUpperCase()}
                </p>
                <h3
                  className="text-[18px] font-semibold mt-[4px]"
                  style={{ color: "var(--text-primary)" }}
                >
                  {question.short_title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowTranscriptModal(false)}
                className="h-[30px] px-[12px] rounded-[6px] text-[11px] font-medium cursor-pointer"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  color: "var(--text-primary)",
                }}
              >
                Close
              </button>
            </div>

            <div
              className="rounded-[10px] border p-[18px] mb-[18px]"
              style={{
                backgroundColor: "var(--surface-subtle)",
                borderColor: "var(--border-default)",
              }}
            >
              <p
                className="text-[14px] leading-[1.65] whitespace-pre-wrap"
                style={{ color: "var(--text-body)" }}
              >
                {dm.annotated_transcript || attempt.transcript_verbatim}
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-[10px] mb-[16px]">
              <div
                className="rounded-[8px] p-[12px]"
                style={{ backgroundColor: "var(--surface-subtle)" }}
              >
                <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                  Words
                </p>
                <p className="text-[15px] font-semibold mt-[2px]" style={{ color: "var(--text-primary)" }}>
                  {dm.word_count}
                </p>
              </div>
              <div
                className="rounded-[8px] p-[12px]"
                style={{ backgroundColor: "var(--surface-subtle)" }}
              >
                <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                  Pace
                </p>
                <p className="text-[15px] font-semibold mt-[2px]" style={{ color: "var(--text-primary)" }}>
                  {dm.speaking_pace_wpm} WPM
                </p>
              </div>
              <div
                className="rounded-[8px] p-[12px]"
                style={{ backgroundColor: "var(--surface-subtle)" }}
              >
                <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                  Fillers
                </p>
                <p className="text-[15px] font-semibold mt-[2px]" style={{ color: "var(--text-primary)" }}>
                  {dm.filler_count} ({dm.filler_per_min}/m)
                </p>
              </div>
              <div
                className="rounded-[8px] p-[12px]"
                style={{ backgroundColor: "var(--surface-subtle)" }}
              >
                <p className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                  Graded by
                </p>
                <p className="text-[12px] font-semibold mt-[4px] truncate" style={{ color: "var(--text-primary)" }}>
                  {evaluation.llm_model || evaluation.llm_provider}
                </p>
              </div>
            </div>

            {Object.keys(dm.filler_breakdown).length > 0 && (
              <div className="flex flex-wrap gap-[8px]">
                {Object.entries(dm.filler_breakdown).map(([word, count]) => (
                  <span
                    key={word}
                    className="px-[9px] py-[4px] rounded-[5px] text-[11px]"
                    style={{
                      backgroundColor: "var(--surface-warning)",
                      color: "var(--text-warning)",
                    }}
                  >
                    “{word}” × {count}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
