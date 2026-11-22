"use client";

import React from "react";
import type { NavTab } from "@/types/rehearse";

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  sessionsThisWeek: number;
  weeklyGoal: number;
  theme: "dark" | "light";
  onChangeTheme: (theme: "dark" | "light") => void;
  candidateName: string;
}

const NAV_ITEMS: { id: NavTab; index: string; label: string }[] = [
  { id: "overview", index: "01", label: "Overview" },
  { id: "practice", index: "02", label: "Practice room" },
  { id: "sessions", index: "03", label: "My sessions" },
  { id: "study", index: "04", label: "Study plan" },
];

export default function Sidebar({
  activeTab,
  onSelectTab,
  sessionsThisWeek,
  weeklyGoal,
  theme,
  onChangeTheme,
  candidateName,
}: SidebarProps) {
  const goal = Math.max(1, weeklyGoal);
  const clamped = Math.min(sessionsThisWeek, goal);
  const progressPct = Math.round((clamped / goal) * 100);

  return (
    <aside
      className="w-[216px] shrink-0 min-h-screen flex flex-col justify-between border-r select-none"
      style={{
        backgroundColor: "var(--surface-chrome)",
        borderColor: "var(--border-chrome)",
      }}
    >
      <div>
        {/* Brand */}
        <div className="px-[26px] pt-[32px] pb-[44px] flex items-baseline gap-[6px]">
          <button
            type="button"
            onClick={() => onSelectTab("practice")}
            className="flex items-baseline gap-[5px] cursor-pointer text-left focus:outline-none"
          >
            <span
              className="text-[27px] font-bold tracking-[-0.02em] leading-none"
              style={{ color: "var(--text-primary)" }}
            >
              rehearse
            </span>
            <span
              className="inline-block w-[6px] h-[6px] rounded-[3px] shrink-0"
              style={{ backgroundColor: "var(--brand-mark)" }}
            />
          </button>
        </div>

        {/* Navigation */}
        <div className="px-[24px] mb-[18px]">
          <p
            className="text-[9px] font-semibold tracking-[0.06em] uppercase"
            style={{ color: "var(--text-nav-secondary)" }}
          >
            YOUR INTERVIEW WORKSPACE
          </p>
        </div>

        <nav className="px-[12px] space-y-[8px]">
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className="w-full h-[44px] rounded-[9px] px-[14px] flex items-center gap-[18px] text-left transition-colors cursor-pointer"
                style={{
                  backgroundColor: isActive ? "var(--surface-navigation-active)" : "transparent",
                }}
              >
                <span
                  className="text-[11px] font-medium tabular-nums"
                  style={{
                    color: isActive ? "var(--text-primary)" : "var(--text-nav-secondary)",
                  }}
                >
                  {item.index}
                </span>
                <span
                  className={`text-[13px] ${isActive ? "font-semibold" : "font-medium"}`}
                  style={{
                    color: isActive ? "var(--text-primary)" : "var(--text-nav-secondary)",
                  }}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Divider */}
        <div
          className="mx-[24px] my-[36px] h-px"
          style={{ backgroundColor: "var(--border-chrome)" }}
        />

        {/* Weekly progress */}
        <div className="px-[24px]">
          <p
            className="text-[10px] font-semibold tracking-[0.05em] uppercase mb-[14px]"
            style={{ color: "var(--text-nav-secondary)" }}
          >
            THIS WEEK
          </p>
          <div
            className="text-[18px] font-semibold leading-[1.25] mb-[18px]"
            style={{ color: "var(--text-primary)" }}
          >
            <p className="m-0">Small steps.</p>
            <p className="m-0">Stronger answers.</p>
          </div>
          <p
            className="text-[11px] font-normal mb-[14px]"
            style={{ color: "var(--text-nav-secondary)" }}
          >
            {sessionsThisWeek} of {goal} practice sessions
          </p>
          <div
            className="w-full h-[5px] rounded-[3px] overflow-hidden"
            style={{ backgroundColor: "var(--border-chrome)" }}
          >
            <div
              className="h-full rounded-[3px] transition-all duration-500"
              style={{
                width: `${Math.max(progressPct, sessionsThisWeek > 0 ? 12 : 0)}%`,
                backgroundColor: "var(--indicator-progress)",
              }}
            />
          </div>
        </div>
      </div>

      {/* Bottom: Appearance switch + Profile */}
      <div className="pt-[36px] pb-[28px]">
        <div className="px-[24px] mb-[28px]">
          <p
            className="text-[10px] font-medium tracking-[0.05em] uppercase mb-[12px]"
            style={{ color: "var(--text-nav-secondary)" }}
          >
            APPEARANCE
          </p>
          <div
            className="h-[40px] w-[168px] rounded-[9px] p-[4px] grid grid-cols-2 gap-[4px]"
            style={{ backgroundColor: "var(--appearance-track)" }}
          >
            <button
              type="button"
              onClick={() => onChangeTheme("light")}
              className="h-[32px] rounded-[6px] text-[11px] font-medium transition-colors cursor-pointer"
              style={{
                backgroundColor:
                  theme === "light" ? "var(--appearance-light-bg)" : "transparent",
                color:
                  theme === "light"
                    ? "var(--appearance-light-text)"
                    : "var(--text-secondary)",
              }}
            >
              Light
            </button>
            <button
              type="button"
              onClick={() => onChangeTheme("dark")}
              className="h-[32px] rounded-[6px] text-[11px] font-medium transition-colors cursor-pointer"
              style={{
                backgroundColor:
                  theme === "dark" ? "var(--appearance-dark-bg)" : "transparent",
                color:
                  theme === "dark"
                    ? "var(--appearance-dark-text)"
                    : "var(--text-secondary)",
              }}
            >
              Dark
            </button>
          </div>
        </div>

        <div
          className="mx-[24px] mb-[24px] h-px"
          style={{ backgroundColor: "var(--border-chrome)" }}
        />

        <div className="px-[24px]">
          <p
            className="text-[13px] font-semibold leading-snug truncate"
            style={{ color: "var(--text-primary)" }}
          >
            {candidateName || "Alex Morgan"}
          </p>
          <p
            className="text-[11px] font-normal mt-[4px]"
            style={{ color: "var(--text-nav-secondary)" }}
          >
            Personal workspace
          </p>
        </div>
      </div>
    </aside>
  );
}
