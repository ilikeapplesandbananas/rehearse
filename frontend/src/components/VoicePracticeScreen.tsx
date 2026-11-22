"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  PristineVoiceRecorder,
  WAVEFORM_BAR_COUNT,
  listAudioInputDevices,
  speakQuestionAloud,
  stopSpeakingQuestion,
  type AudioInputDevice,
  type RecorderState,
} from "@/lib/audio-recorder";
import type { InterviewSession, SessionQuestion } from "@/types/rehearse";

interface VoicePracticeScreenProps {
  session: InterviewSession;
  questionIndex: number;
  onSelectQuestion: (idx: number, openReviewIfDone?: boolean) => void;
  onSubmitAnswer: (params: {
    questionId: string;
    audioBlob: Blob | null;
    transcript: string;
    durationSeconds: number;
  }) => Promise<void>;
  onSaveAndExit: () => void;
}

const DEFAULT_IDLE_BARS = Array.from({ length: WAVEFORM_BAR_COUNT }, (_, i) => {
  const wave = Math.abs(Math.sin(i * 0.48) * 0.55 + Math.cos(i * 1.15) * 0.35);
  return Math.max(0.11, Math.min(0.92, wave));
});

function formatTimer(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function VoicePracticeScreen({
  session,
  questionIndex,
  onSelectQuestion,
  onSubmitAnswer,
  onSaveAndExit,
}: VoicePracticeScreenProps) {
  const question: SessionQuestion | undefined = session.questions[questionIndex];
  const recorderRef = useRef<PristineVoiceRecorder | null>(null);

  const [state, setState] = useState<RecorderState>("idle");
  const [elapsedSec, setElapsedSec] = useState(0);
  const [bars, setBars] = useState<number[]>(DEFAULT_IDLE_BARS);
  const [activeCursor, setActiveCursor] = useState(0);
  const [micMessage, setMicMessage] = useState(
    "Click Start recording when you’re ready to answer aloud"
  );
  const [finalTranscript, setFinalTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [manualMode, setManualMode] = useState(false);
  const [speakingQuestion, setSpeakingQuestion] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [devices, setDevices] = useState<AudioInputDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");

  // Reset recorder state when switching questions
  useEffect(() => {
    recorderRef.current?.abort();
    stopSpeakingQuestion();
    setState("idle");
    setElapsedSec(0);
    setBars(DEFAULT_IDLE_BARS);
    setActiveCursor(0);
    setMicMessage("Click Start recording when you’re ready to answer aloud");
    setFinalTranscript("");
    setInterimTranscript("");
    setRecordedBlob(null);
    setErrorMsg("");
    setManualMode(false);
    setPlaybackUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
  }, [question?.id]);

  // Enumerate microphones on mount
  useEffect(() => {
    listAudioInputDevices().then((list) => {
      setDevices(list);
      if (list.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(list[0].deviceId);
      }
    });
    return () => {
      recorderRef.current?.abort();
      stopSpeakingQuestion();
    };
  }, []);

  if (!question) return null;

  const qNum = String(questionIndex + 1).padStart(2, "0");
  const totalQ = String(session.questions.length).padStart(2, "0");
  const estMin = Math.round(session.questions.length * 3.3);
  const liveDisplay = `${finalTranscript} ${interimTranscript}`.replace(/\s+/g, " ").trim();

  async function handleStartRecording() {
    setErrorMsg("");
    stopSpeakingQuestion();
    setSpeakingQuestion(false);

    const rec = new PristineVoiceRecorder({
      onWaveform: (nextBars, cursor) => {
        setBars(nextBars);
        setActiveCursor(cursor);
      },
      onMicHealth: (msg) => setMicMessage(msg),
      onLiveTranscript: (fin, inter) => {
        setFinalTranscript(fin);
        setInterimTranscript(inter);
      },
      onDurationTick: (sec) => setElapsedSec(sec),
      onError: (msg) => setErrorMsg(msg),
    });
    recorderRef.current = rec;

    try {
      await rec.start(selectedDeviceId || undefined);
      setState("recording");
      // Refresh device labels now that mic permission was granted
      const updated = await listAudioInputDevices();
      if (updated.length > 0) setDevices(updated);
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Could not access your microphone. You can also type your answer below."
      );
      setState("idle");
    }
  }

  function handlePauseResume() {
    if (state === "recording") {
      recorderRef.current?.pause();
      setState("paused");
    } else if (state === "paused") {
      recorderRef.current?.resume();
      setState("recording");
    }
  }

  async function handleStopToReview() {
    if (!recorderRef.current) return;
    const { blob, durationSeconds, liveTranscript } = await recorderRef.current.stop();
    setRecordedBlob(blob);
    setElapsedSec(durationSeconds);
    if (liveTranscript) {
      setFinalTranscript(liveTranscript);
      setInterimTranscript("");
    }
    setPlaybackUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return blob.size > 0 ? URL.createObjectURL(blob) : null;
    });
    setState("review");
    setMicMessage("Review your take, re-record, or submit for structured coaching");
  }

  async function handleFinishAndEvaluate() {
    if (!question) return;
    setErrorMsg("");
    let blobToSend = recordedBlob;
    let durationToSend = elapsedSec;
    let transcriptToSend = liveDisplay;

    if (state === "recording" || state === "paused") {
      if (recorderRef.current) {
        const stopped = await recorderRef.current.stop();
        blobToSend = stopped.blob;
        durationToSend = stopped.durationSeconds;
        transcriptToSend = stopped.liveTranscript || transcriptToSend;
        setRecordedBlob(blobToSend);
        setElapsedSec(durationToSend);
        setFinalTranscript(transcriptToSend);
        setInterimTranscript("");
      }
    }

    if (!blobToSend?.size && transcriptToSend.trim().length < 5) {
      setErrorMsg("Please record your spoken answer (or type it in the transcript box) first.");
      setState("idle");
      return;
    }

    setState("submitting");
    setMicMessage("Transcribing verbatim speech & evaluating against rubric…");
    try {
      await onSubmitAnswer({
        questionId: question.id,
        audioBlob: blobToSend,
        transcript: transcriptToSend,
        durationSeconds: Math.max(durationToSend, 1),
      });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Evaluation failed. Please try again.");
      setState("review");
      setMicMessage("Evaluation paused. Review your answer and try submitting again.");
    }
  }

  function handleReRecord() {
    recorderRef.current?.abort();
    setState("idle");
    setElapsedSec(0);
    setFinalTranscript("");
    setInterimTranscript("");
    setRecordedBlob(null);
    setBars(DEFAULT_IDLE_BARS);
    setActiveCursor(0);
    setErrorMsg("");
    setMicMessage("Click Start recording when you’re ready to try again");
    setPlaybackUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
  }

  async function handleListenAgain() {
    if (!question) return;
    if (speakingQuestion) {
      stopSpeakingQuestion();
      setSpeakingQuestion(false);
      return;
    }
    await speakQuestionAloud(
      question.question_text,
      () => setSpeakingQuestion(true),
      () => setSpeakingQuestion(false)
    );
  }

  const badgeText =
    state === "recording"
      ? "●  RECORDING"
      : state === "paused"
      ? "Ⅱ  PAUSED"
      : state === "submitting"
      ? "●  EVALUATING"
      : state === "review"
      ? "✓  CAPTURED"
      : "●  READY";

  return (
    <div className="w-full max-w-[1128px] mx-auto">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-[16px] mb-[26px]">
        <div>
          <h1
            className="text-[32px] font-semibold leading-[1.3] tracking-[-0.02em]"
            style={{ color: "var(--text-primary)" }}
          >
            Your experience, out loud.
          </h1>
          <p
            className="text-[14px] font-normal mt-[8px]"
            style={{ color: "var(--text-secondary)" }}
          >
            {session.target_role} at {session.company_name} &nbsp;/&nbsp; Personalized practice
          </p>
        </div>

        <button
          type="button"
          onClick={onSaveAndExit}
          className="h-[38px] px-[24px] rounded-[7px] border text-[12px] font-medium shrink-0 self-start transition-opacity hover:opacity-85 cursor-pointer"
          style={{
            backgroundColor: "var(--surface-card)",
            borderColor: "var(--border-default)",
            color: "var(--text-primary)",
          }}
        >
          Save &amp; exit
        </button>
      </div>

      {/* Segmented Question Progress Bars */}
      <div
        className="grid gap-[14px] mb-[28px]"
        style={{
          gridTemplateColumns: `repeat(${session.questions.length}, minmax(0, 1fr))`,
        }}
      >
        {session.questions.map((q, idx) => {
          const isCurrent = idx === questionIndex;
          const isCompleted = q.status === "completed";
          const bg = isCurrent
            ? "var(--text-primary)"
            : isCompleted
            ? "var(--indicator-completed)"
            : "var(--border-default)";
          return (
            <button
              key={q.id}
              type="button"
              onClick={() => onSelectQuestion(idx, false)}
              title={`Question ${idx + 1}: ${q.short_title}`}
              className="h-[4px] rounded-[2px] cursor-pointer transition-colors"
              style={{ backgroundColor: bg }}
            />
          );
        })}
      </div>

      {/* Main 2-Column Layout matching Figma 744 / 360 ratio */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,744fr)_minmax(0,360fr)] gap-[24px] items-start">
        {/* Left Column */}
        <div className="space-y-[20px]">
          {/* Current Interview Question Card */}
          <section
            className="rounded-[14px] border p-[24px] min-h-[252px] flex flex-col justify-between"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <div>
              <div className="flex flex-wrap items-center gap-[10px] mb-[26px]">
                <span
                  className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center tracking-[0.02em]"
                  style={{
                    backgroundColor: "var(--surface-subtle)",
                    color: "var(--text-primary)",
                  }}
                >
                  QUESTION {qNum} / {totalQ}
                </span>
                <span
                  className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                  style={{
                    backgroundColor: "var(--surface-category)",
                    color: "var(--text-category)",
                  }}
                >
                  {question.category}
                </span>
              </div>

              <h2
                className="text-[24px] sm:text-[26px] font-semibold leading-[1.42] tracking-[-0.015em]"
                style={{ color: "var(--text-primary)" }}
              >
                {question.question_text}
              </h2>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-[28px]">
              <p className="text-[11px] font-normal" style={{ color: "var(--text-secondary)" }}>
                {question.source_attribution}
              </p>
              <button
                type="button"
                onClick={handleListenAgain}
                className="text-[11px] font-medium cursor-pointer hover:underline"
                style={{ color: "var(--text-primary)" }}
              >
                {speakingQuestion ? "Stop audio" : "Listen again"}
              </button>
            </div>
          </section>

          {/* Voice Recording Card (Deep Forest #203326) */}
          <section
            className="rounded-[14px] p-[24px] min-h-[257px] flex flex-col justify-between"
            style={{ backgroundColor: "var(--surface-feature)" }}
          >
            {/* Top Status + Timer */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-[10px]">
                <span
                  className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center gap-[6px]"
                  style={{
                    backgroundColor: "var(--surface-feature-control)",
                    color: "var(--text-recording)",
                  }}
                >
                  {badgeText}
                </span>

                {state === "idle" && devices.length > 1 && (
                  <select
                    value={selectedDeviceId}
                    onChange={(e) => setSelectedDeviceId(e.target.value)}
                    aria-label="Select microphone"
                    className="h-[28px] max-w-[200px] rounded-[6px] px-[8px] text-[10px] focus:outline-none cursor-pointer"
                    style={{
                      backgroundColor: "var(--surface-feature-control)",
                      color: "var(--text-feature-muted)",
                    }}
                  >
                    {devices.map((d) => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.label}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <span
                className="text-[18px] font-medium tabular-nums"
                style={{ color: "var(--text-feature-control)" }}
              >
                {formatTimer(elapsedSec)}
              </span>
            </div>

            {/* Live 77-bar Waveform */}
            <div className="my-[22px] px-[12px] sm:px-[36px] h-[74px] flex items-center justify-between gap-[3px]">
              {bars.map((amp, i) => {
                const pxHeight = Math.max(8, Math.round(amp * 70));
                const isLit =
                  state === "recording" || state === "paused"
                    ? i < activeCursor
                    : state === "review" || state === "submitting"
                    ? true
                    : i < 42;
                return (
                  <div
                    key={i}
                    className="w-[3px] rounded-[2px] transition-all duration-100 shrink-0"
                    style={{
                      height: `${pxHeight}px`,
                      backgroundColor: isLit
                        ? "var(--accent-lime)"
                        : "var(--indicator-wave-muted)",
                      opacity: state === "idle" ? 0.65 : 1,
                    }}
                  />
                );
              })}
            </div>

            {/* Mic feedback + Playback preview if in review */}
            <div className="flex flex-col items-center gap-[12px]">
              <p
                className="text-[11px] font-normal text-center"
                style={{ color: "var(--text-mic-feedback)" }}
              >
                {micMessage}
              </p>

              {state === "review" && playbackUrl && (
                <audio
                  controls
                  src={playbackUrl}
                  className="h-[30px] max-w-[320px] opacity-90"
                />
              )}

              {/* Controls */}
              <div className="flex flex-wrap items-center justify-center gap-[12px]">
                {state === "idle" && (
                  <>
                    <button
                      type="button"
                      onClick={handleStartRecording}
                      className="h-[34px] px-[22px] rounded-[6px] text-[11px] font-semibold cursor-pointer transition-opacity hover:opacity-95"
                      style={{
                        backgroundColor: "var(--accent-lime)",
                        color: "var(--text-on-lime)",
                      }}
                    >
                      ● &nbsp;Start recording
                    </button>
                    {liveDisplay.length >= 10 && (
                      <button
                        type="button"
                        onClick={handleFinishAndEvaluate}
                        className="h-[34px] px-[18px] rounded-[6px] text-[11px] font-medium cursor-pointer"
                        style={{
                          backgroundColor: "var(--surface-feature-control)",
                          color: "var(--text-feature-control)",
                        }}
                      >
                        Evaluate typed answer &nbsp;→
                      </button>
                    )}
                  </>
                )}

                {(state === "recording" || state === "paused") && (
                  <>
                    <button
                      type="button"
                      onClick={handlePauseResume}
                      className="h-[32px] min-w-[100px] px-[18px] rounded-[6px] text-[11px] font-medium cursor-pointer transition-opacity hover:opacity-90"
                      style={{
                        backgroundColor: "var(--surface-feature-control)",
                        color: "var(--text-feature-control)",
                      }}
                    >
                      {state === "recording" ? "Ⅱ   Pause" : "▶   Resume"}
                    </button>

                    {state === "paused" && (
                      <button
                        type="button"
                        onClick={handleStopToReview}
                        className="h-[32px] px-[14px] rounded-[6px] text-[11px] font-medium cursor-pointer transition-opacity hover:opacity-90"
                        style={{
                          backgroundColor: "var(--surface-feature-control)",
                          color: "var(--text-feature-muted)",
                        }}
                      >
                        Review take
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={handleFinishAndEvaluate}
                      className="h-[32px] min-w-[169px] px-[22px] rounded-[6px] text-[11px] font-semibold cursor-pointer transition-opacity hover:opacity-95"
                      style={{
                        backgroundColor: "var(--accent-lime)",
                        color: "var(--text-on-lime)",
                      }}
                    >
                      Finish answer &nbsp;→
                    </button>
                  </>
                )}

                {state === "review" && (
                  <>
                    <button
                      type="button"
                      onClick={handleReRecord}
                      className="h-[32px] px-[18px] rounded-[6px] text-[11px] font-medium cursor-pointer"
                      style={{
                        backgroundColor: "var(--surface-feature-control)",
                        color: "var(--text-feature-control)",
                      }}
                    >
                      ↻ &nbsp;Re-record
                    </button>
                    <button
                      type="button"
                      onClick={handleFinishAndEvaluate}
                      className="h-[32px] px-[22px] rounded-[6px] text-[11px] font-semibold cursor-pointer"
                      style={{
                        backgroundColor: "var(--accent-lime)",
                        color: "var(--text-on-lime)",
                      }}
                    >
                      Submit &amp; grade &nbsp;→
                    </button>
                  </>
                )}

                {state === "submitting" && (
                  <span
                    className="h-[32px] px-[20px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                    style={{
                      backgroundColor: "var(--surface-feature-control)",
                      color: "var(--accent-lime)",
                    }}
                  >
                    Analyzing transcript, pace, pauses &amp; technical depth…
                  </span>
                )}
              </div>
            </div>
          </section>

          {errorMsg && (
            <div
              className="rounded-[9px] px-[16px] py-[12px] text-[12px]"
              style={{
                backgroundColor: "var(--surface-warning)",
                color: "var(--text-warning)",
              }}
            >
              {errorMsg}
            </div>
          )}

          {/* Live Answer Transcript Card */}
          <section
            className="rounded-[14px] border p-[24px] min-h-[197px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <div className="flex items-center justify-between gap-3 mb-[18px]">
              <div className="flex items-center gap-[12px]">
                <h3
                  className="text-[15px] font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  Live transcript
                </h3>
                {state !== "recording" && state !== "submitting" && (
                  <button
                    type="button"
                    onClick={() => setManualMode((v) => !v)}
                    className="text-[11px] cursor-pointer hover:underline"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {manualMode ? "Done editing" : "Edit / type instead"}
                  </button>
                )}
              </div>

              <span
                className="h-[28px] px-[11px] rounded-[6px] text-[11px] font-medium inline-flex items-center"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  color: "var(--text-primary)",
                }}
              >
                Only visible to you
              </span>
            </div>

            {manualMode ? (
              <textarea
                value={finalTranscript}
                onChange={(e) => {
                  setFinalTranscript(e.target.value);
                  setInterimTranscript("");
                }}
                rows={4}
                placeholder="Speak aloud above, or type/paste your answer here to test evaluation without a microphone..."
                className="w-full rounded-[7px] border p-[12px] text-[14px] leading-[1.5] focus:outline-none"
                style={{
                  backgroundColor: "var(--surface-subtle)",
                  borderColor: "var(--border-default)",
                  color: "var(--text-primary)",
                }}
              />
            ) : liveDisplay ? (
              <p
                className="text-[15px] font-normal leading-[1.55]"
                style={{ color: "var(--text-body)" }}
              >
                “{liveDisplay}
                {state === "recording" ? "…”" : "”"}
              </p>
            ) : (
              <p
                className="text-[14px] font-normal leading-[1.55]"
                style={{ color: "var(--text-secondary)" }}
              >
                {state === "recording"
                  ? "Listening closely. Start speaking and your live words will appear here. Full verbatim audio is captured simultaneously for precision transcription."
                  : "Your spoken words will appear here in real time while you answer. Full high-bitrate audio is recorded so filler words and pauses are measured accurately."}
              </p>
            )}
          </section>

          <p className="text-[11px] font-normal" style={{ color: "var(--text-secondary)" }}>
            Take your time. You can review and re-record before submitting.
          </p>
        </div>

        {/* Right Column */}
        <div className="space-y-[20px]">
          {/* Session Question Queue Card */}
          <section
            className="rounded-[14px] border p-[24px]"
            style={{
              backgroundColor: "var(--surface-card)",
              borderColor: "var(--border-default)",
            }}
          >
            <h3
              className="text-[17px] font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Your session
            </h3>
            <p
              className="text-[11px] font-normal mt-[6px] mb-[22px]"
              style={{ color: "var(--text-secondary)" }}
            >
              {session.questions.length} questions &nbsp;·&nbsp; About {estMin} minutes
            </p>

            <div className="space-y-[6px] -mx-[12px]">
              {session.questions.map((q, idx) => {
                const isCurrent = idx === questionIndex;
                const isDone = q.status === "completed";
                return (
                  <button
                    key={q.id}
                    type="button"
                    onClick={() => onSelectQuestion(idx, isDone && !isCurrent)}
                    className="w-full rounded-[7px] px-[12px] py-[10px] flex items-start gap-[16px] text-left transition-colors cursor-pointer"
                    style={{
                      backgroundColor: isCurrent
                        ? "var(--surface-current-question)"
                        : "transparent",
                    }}
                  >
                    <span
                      className="text-[12px] font-medium tabular-nums mt-[2px] w-[18px] shrink-0"
                      style={{
                        color: isDone
                          ? "var(--text-completed)"
                          : "var(--text-secondary)",
                      }}
                    >
                      {isDone ? "✓" : String(idx + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p
                        className={`text-[12px] truncate ${
                          isCurrent ? "font-semibold" : "font-medium"
                        }`}
                        style={{ color: "var(--text-primary)" }}
                      >
                        {q.short_title}
                      </p>
                      <p
                        className="text-[10px] mt-[3px]"
                        style={{
                          color: isCurrent
                            ? "var(--text-completed)"
                            : "var(--text-secondary)",
                        }}
                      >
                        {isCurrent
                          ? "In progress"
                          : isDone
                          ? `Completed${
                              q.latest_attempt
                                ? ` · ${q.latest_attempt.evaluation.scores.overall}/100`
                                : ""
                            }`
                          : "Up next"}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Answer Guidance Olive Card */}
          <section
            className="rounded-[14px] p-[24px]"
            style={{ backgroundColor: "var(--surface-advice)" }}
          >
            <h3
              className="text-[19px] font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              A little room to think.
            </h3>
            <p
              className="text-[13px] font-normal leading-[1.5] mt-[12px] mb-[26px]"
              style={{ color: "var(--text-advice)" }}
            >
              You don’t need a perfect script. Make your reasoning easy to follow.
            </p>

            <div className="space-y-[18px]">
              {(question.guidance_cues?.length
                ? question.guidance_cues
                : [
                    "Start with the big picture",
                    "Explain the choices you made",
                    "Close with impact and learning",
                  ]
              ).map((cue, idx) => (
                <div key={idx} className="flex items-start gap-[16px]">
                  <span
                    className="text-[10px] font-semibold tabular-nums mt-[2px]"
                    style={{ color: "var(--text-advice-index)" }}
                  >
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <p
                    className="text-[12px] font-medium leading-snug"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {cue}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
