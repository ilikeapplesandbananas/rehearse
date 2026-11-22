"use client";

import React, { useState } from "react";
import { updateEngineKeys } from "@/lib/api";
import type { EngineSettingsStatus } from "@/types/rehearse";

interface HelpModalProps {
  open: boolean;
  onClose: () => void;
  engineStatus: EngineSettingsStatus | null;
  onStatusUpdated: (status: EngineSettingsStatus) => void;
}

export default function HelpModal({
  open,
  onClose,
  engineStatus,
  onStatusUpdated,
}: HelpModalProps) {
  const [geminiKey, setGeminiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [deepgramKey, setDeepgramKey] = useState("");
  const [tavilyKey, setTavilyKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  if (!open) return null;

  async function handleSaveKeys(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const payload: Record<string, string> = {};
      if (geminiKey.trim()) payload.GEMINI_API_KEY = geminiKey.trim();
      if (anthropicKey.trim()) payload.ANTHROPIC_API_KEY = anthropicKey.trim();
      if (openaiKey.trim()) payload.OPENAI_API_KEY = openaiKey.trim();
      if (deepgramKey.trim()) payload.DEEPGRAM_API_KEY = deepgramKey.trim();
      if (tavilyKey.trim()) payload.TAVILY_API_KEY = tavilyKey.trim();

      const updated = await updateEngineKeys(payload);
      onStatusUpdated(updated);
      setGeminiKey("");
      setAnthropicKey("");
      setOpenaiKey("");
      setDeepgramKey("");
      setTavilyKey("");
      setMessage("Saved to local backend .env and activated immediately.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to save keys.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[640px] max-h-[88vh] overflow-y-auto rounded-[14px] border p-[28px]"
        style={{
          backgroundColor: "var(--surface-card)",
          borderColor: "var(--border-default)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 mb-[20px]">
          <div>
            <p
              className="text-[10px] font-semibold uppercase tracking-[0.06em] mb-[6px]"
              style={{ color: "var(--text-list-index)" }}
            >
              ENGINES &amp; RESOURCES
            </p>
            <h2
              className="text-[22px] font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              AI Evaluation &amp; Verbatim Speech Setup
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-[32px] px-[12px] rounded-[7px] text-[12px] font-medium cursor-pointer"
            style={{
              backgroundColor: "var(--surface-subtle)",
              color: "var(--text-primary)",
            }}
          >
            Close
          </button>
        </div>

        {/* Active engine status pills */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-[12px] mb-[24px]">
          <div
            className="rounded-[10px] border p-[14px]"
            style={{
              backgroundColor: "var(--surface-subtle)",
              borderColor: "var(--border-default)",
            }}
          >
            <p className="text-[10px] uppercase tracking-[0.05em] mb-[4px]" style={{ color: "var(--text-secondary)" }}>
              LLM Evaluator
            </p>
            <p className="text-[13px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {engineStatus?.llm.model || "local_coach"}
            </p>
            <p
              className="text-[10px] mt-[4px]"
              style={{
                color: engineStatus?.llm.frontier_enabled
                  ? "var(--text-success)"
                  : "var(--text-warning)",
              }}
            >
              {engineStatus?.llm.frontier_enabled ? "Frontier reasoning active" : "Add API key below"}
            </p>
          </div>

          <div
            className="rounded-[10px] border p-[14px]"
            style={{
              backgroundColor: "var(--surface-subtle)",
              borderColor: "var(--border-default)",
            }}
          >
            <p className="text-[10px] uppercase tracking-[0.05em] mb-[4px]" style={{ color: "var(--text-secondary)" }}>
              Verbatim STT
            </p>
            <p className="text-[13px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {engineStatus?.stt.provider === "deepgram"
                ? `Deepgram ${engineStatus.stt.model}`
                : engineStatus?.stt.provider === "gemini_audio"
                ? `Gemini ${engineStatus.stt.model}`
                : engineStatus?.stt.provider || "browser_live"}
            </p>
            <p
              className="text-[10px] mt-[4px]"
              style={{
                color: engineStatus?.stt.cloud_verbatim_enabled
                  ? "var(--text-success)"
                  : "var(--text-secondary)",
              }}
            >
              {engineStatus?.stt.cloud_verbatim_enabled
                ? "Verbatim audio + pauses"
                : "Browser live transcript"}
            </p>
          </div>

          <div
            className="rounded-[10px] border p-[14px]"
            style={{
              backgroundColor: "var(--surface-subtle)",
              borderColor: "var(--border-default)",
            }}
          >
            <p className="text-[10px] uppercase tracking-[0.05em] mb-[4px]" style={{ color: "var(--text-secondary)" }}>
              Voice Question TTS
            </p>
            <p className="text-[13px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {engineStatus?.tts.provider || "browser_speech"}
            </p>
            <p className="text-[10px] mt-[4px]" style={{ color: "var(--text-secondary)" }}>
              Instant question playback
            </p>
          </div>
        </div>

        {/* Key form */}
        <form onSubmit={handleSaveKeys} className="space-y-[14px]">
          <p className="text-[12px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Connect a frontier LLM (<strong style={{ color: "var(--text-primary)" }}>Gemini 2.5 Pro</strong>,{" "}
            <strong style={{ color: "var(--text-primary)" }}>Claude Sonnet 4</strong>, or{" "}
            <strong style={{ color: "var(--text-primary)" }}>OpenAI GPT-4.1</strong>) and{" "}
            <strong style={{ color: "var(--text-primary)" }}>Deepgram Nova-3</strong> (for exact word-level pause timestamps and verbatim filler capture). Keys are stored locally in <code className="text-[11px]">backend/.env</code>.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-[12px]">
            <div>
              <label className="block text-[11px] font-medium mb-[6px]" style={{ color: "var(--text-primary)" }}>
                Gemini API Key {engineStatus?.keys_configured?.GEMINI_API_KEY && "✓"}
              </label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIza..."
                className="w-full h-[38px] rounded-[7px] border px-[12px] text-[12px] focus:outline-none"
                style={{
                  backgroundColor: "var(--bg-canvas)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium mb-[6px]" style={{ color: "var(--text-primary)" }}>
                Deepgram API Key (STT) {engineStatus?.keys_configured?.DEEPGRAM_API_KEY && "✓"}
              </label>
              <input
                type="password"
                value={deepgramKey}
                onChange={(e) => setDeepgramKey(e.target.value)}
                placeholder="dg_..."
                className="w-full h-[38px] rounded-[7px] border px-[12px] text-[12px] focus:outline-none"
                style={{
                  backgroundColor: "var(--bg-canvas)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium mb-[6px]" style={{ color: "var(--text-primary)" }}>
                Anthropic API Key {engineStatus?.keys_configured?.ANTHROPIC_API_KEY && "✓"}
              </label>
              <input
                type="password"
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full h-[38px] rounded-[7px] border px-[12px] text-[12px] focus:outline-none"
                style={{
                  backgroundColor: "var(--bg-canvas)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium mb-[6px]" style={{ color: "var(--text-primary)" }}>
                OpenAI API Key (LLM + Whisper) {engineStatus?.keys_configured?.OPENAI_API_KEY && "✓"}
              </label>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full h-[38px] rounded-[7px] border px-[12px] text-[12px] focus:outline-none"
                style={{
                  backgroundColor: "var(--bg-canvas)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                }}
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium mb-[6px]" style={{ color: "var(--text-primary)" }}>
              Tavily API Key (Optional Live Web Research Boost) {engineStatus?.keys_configured?.TAVILY_API_KEY && "✓"}
            </label>
            <input
              type="password"
              value={tavilyKey}
              onChange={(e) => setTavilyKey(e.target.value)}
              placeholder="tvly-... (optional, curated company DB & DuckDuckGo work without a key)"
              className="w-full h-[38px] rounded-[7px] border px-[12px] text-[12px] focus:outline-none"
              style={{
                backgroundColor: "var(--bg-canvas)",
                borderColor: "var(--border-default)",
                color: "var(--text-primary)",
              }}
            />
          </div>

          {message && (
            <p className="text-[12px]" style={{ color: "var(--text-success)" }}>
              {message}
            </p>
          )}

          <div className="flex items-center justify-between pt-[8px]">
            <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              All features work out of the box even before adding keys.
            </p>
            <button
              type="submit"
              disabled={saving}
              className="h-[38px] px-[20px] rounded-[8px] text-[12px] font-semibold cursor-pointer disabled:opacity-60"
              style={{
                backgroundColor: "var(--accent-lime)",
                color: "var(--text-on-lime)",
              }}
            >
              {saving ? "Saving..." : "Save & activate"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
