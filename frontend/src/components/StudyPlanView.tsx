"use client";

import React from "react";
import type { StudyPlanRecord } from "@/types/rehearse";

interface StudyPlanViewProps {
  items: StudyPlanRecord[];
  onToggleItem: (id: string, completed: boolean) => Promise<void>;
  onStartNew: () => void;
}

export default function StudyPlanView({
  items,
  onToggleItem,
  onStartNew,
}: StudyPlanViewProps) {
  const remaining = items.filter((i) => !i.completed).length;

  return (
    <div className="w-full max-w-[1128px] mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-[16px] mb-[26px]">
        <div>
          <h1
            className="text-[32px] font-semibold leading-[1.3] tracking-[-0.02em]"
            style={{ color: "var(--text-primary)" }}
          >
            Your targeted study plan.
          </h1>
          <p className="text-[14px] mt-[8px]" style={{ color: "var(--text-secondary)" }}>
            Every technical gap flagged across your answers, turned into focused remediation topics.
          </p>
        </div>

        <span
          className="h-[34px] px-[14px] rounded-[7px] text-[12px] font-medium inline-flex items-center self-start"
          style={{
            backgroundColor: "var(--surface-advice)",
            color: "var(--text-primary)",
          }}
        >
          {remaining} open {remaining === 1 ? "topic" : "topics"}
        </span>
      </div>

      {items.length === 0 ? (
        <div
          className="rounded-[14px] border p-[40px] text-center"
          style={{
            backgroundColor: "var(--surface-card)",
            borderColor: "var(--border-default)",
          }}
        >
          <p className="text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
            No study topics queued yet
          </p>
          <p className="text-[13px] mt-[8px] mb-[20px]" style={{ color: "var(--text-secondary)" }}>
            Complete and evaluate a voice answer in the Practice room to populate tailored study recommendations.
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
            Go to Practice room →
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-[16px]">
          {items.map((item, idx) => (
            <div
              key={item.id}
              className="rounded-[14px] border p-[22px] flex flex-col justify-between transition-opacity"
              style={{
                backgroundColor: item.completed ? "var(--surface-card)" : "var(--surface-advice)",
                borderColor: item.completed ? "var(--border-default)" : "var(--border-advice)",
                opacity: item.completed ? 0.65 : 1,
              }}
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-[10px]">
                  <span
                    className="text-[10px] font-semibold tabular-nums"
                    style={{ color: "var(--text-advice-index)" }}
                  >
                    {String(idx + 1).padStart(2, "0")} · {item.company_name || "Practice"}
                  </span>

                  <button
                    type="button"
                    onClick={() => onToggleItem(item.id, !item.completed)}
                    className="h-[26px] px-[10px] rounded-[5px] text-[10px] font-medium cursor-pointer"
                    style={{
                      backgroundColor: item.completed
                        ? "var(--surface-success)"
                        : "var(--surface-card)",
                      color: item.completed ? "var(--text-success)" : "var(--text-primary)",
                    }}
                  >
                    {item.completed ? "✓ Reviewed" : "Mark reviewed"}
                  </button>
                </div>

                <a
                  href={
                    item.resource_url ||
                    `https://www.google.com/search?q=${encodeURIComponent(
                      item.search_query_or_resource || item.topic
                    )}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[15px] font-semibold inline-flex items-center gap-[8px] hover:underline"
                  style={{ color: "var(--text-primary)" }}
                >
                  <span>{item.topic}</span>
                  <span>↗</span>
                </a>

                {item.subtitle && (
                  <p className="text-[12px] mt-[6px]" style={{ color: "var(--text-primary)" }}>
                    {item.subtitle}
                  </p>
                )}

                <p
                  className="text-[12px] mt-[6px] leading-relaxed"
                  style={{ color: "var(--text-advice)" }}
                >
                  {item.why}
                </p>
              </div>

              <div className="mt-[16px] pt-[12px] border-t flex items-center justify-between" style={{ borderColor: "var(--border-advice)" }}>
                <span className="text-[10px] truncate max-w-[70%]" style={{ color: "var(--text-secondary)" }}>
                  Query: {item.search_query_or_resource}
                </span>
                <a
                  href={
                    item.resource_url ||
                    `https://www.google.com/search?q=${encodeURIComponent(
                      item.search_query_or_resource || item.topic
                    )}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] font-semibold hover:underline"
                  style={{ color: "var(--text-primary)" }}
                >
                  Study ↗
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
