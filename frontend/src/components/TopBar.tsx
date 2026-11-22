"use client";

import React from "react";
import type { EngineSettingsStatus, NavTab, PracticeStage } from "@/types/rehearse";

interface TopBarProps {
  activeTab: NavTab;
  practiceStage: PracticeStage;
  engineStatus: EngineSettingsStatus | null;
  onOpenHelp: () => void;
}

export default function TopBar({
  activeTab,
  practiceStage,
  engineStatus,
  onOpenHelp,
}: TopBarProps) {
  const sectionLabel =
    activeTab === "overview"
      ? "Overview"
      : activeTab === "practice"
      ? "Practice room"
      : activeTab === "sessions"
      ? "My sessions"
      : "Study plan";

  const statusText =
    activeTab === "practice"
      ? practiceStage === "setup"
        ? "New interview"
        : practiceStage === "voice"
        ? "Session in progress"
        : "Session results"
      : activeTab === "overview"
      ? "Workspace pulse"
      : activeTab === "sessions"
      ? "Saved history"
      : "Targeted remediation";

  return (
    <header
      className="h-[80px] w-full shrink-0 border-b flex items-center justify-between px-[32px] lg:px-[48px]"
      style={{
        backgroundColor: "var(--surface-chrome)",
        borderColor: "var(--border-chrome)",
      }}
    >
      <p
        className="text-[13px] font-normal tracking-[-0.005em]"
        style={{ color: "var(--text-nav-secondary)" }}
      >
        Workspace &nbsp;/&nbsp; {sectionLabel}
      </p>

      <div className="flex items-center gap-[28px] lg:gap-[48px]">
        <div className="hidden sm:flex items-center gap-[10px]">
          {engineStatus?.llm.frontier_enabled && (
            <span
              className="text-[10px] font-medium px-[8px] py-[3px] rounded-[5px]"
              style={{
                backgroundColor: "var(--surface-success)",
                color: "var(--text-success)",
              }}
            >
              {engineStatus.llm.model}
            </span>
          )}
          <span
            className="text-[12px] font-normal"
            style={{ color: "var(--text-nav-secondary)" }}
          >
            {statusText}
          </span>
        </div>

        <button
          type="button"
          onClick={onOpenHelp}
          className="h-[36px] px-[18px] rounded-[8px] text-[11px] font-medium transition-opacity hover:opacity-90 cursor-pointer"
          style={{
            backgroundColor: "var(--surface-chrome-control)",
            color: "var(--text-primary)",
          }}
        >
          Help &amp; resources
        </button>
      </div>
    </header>
  );
}
