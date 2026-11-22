"use client";

import { fetchNeuralTTS } from "@/lib/api";

export const WAVEFORM_BAR_COUNT = 77;

export type RecorderState = "idle" | "recording" | "paused" | "review" | "submitting";

export interface AudioInputDevice {
  deviceId: string;
  label: string;
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [altIndex: number]: { transcript: string };
    };
  };
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null;
  onerror: ((ev: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

export function selectBestAudioMimeType(): string {
  if (typeof window === "undefined" || typeof MediaRecorder === "undefined") {
    return "audio/webm";
  }
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/mp4;codecs=mp4a.40.2",
    "audio/ogg;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  for (const mime of candidates) {
    if (MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return "";
}

export async function listAudioInputDevices(): Promise<AudioInputDevice[]> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.enumerateDevices) {
    return [];
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((d) => d.kind === "audioinput")
      .map((d, idx) => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone ${idx + 1}`,
      }));
  } catch {
    return [];
  }
}

export interface PristineRecorderCallbacks {
  onWaveform: (bars: number[], activeIndex: number) => void;
  onMicHealth: (message: string, level: "good" | "quiet" | "idle" | "error") => void;
  onLiveTranscript: (finalText: string, interimText: string) => void;
  onDurationTick: (activeSeconds: number) => void;
  onError: (message: string) => void;
}

export class PristineVoiceRecorder {
  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private rafId: number | null = null;
  private recognition: SpeechRecognitionLike | null = null;

  private isRecording = false;
  private isPaused = false;
  private finalTranscript = "";
  private interimTranscript = "";
  private activeSeconds = 0;
  private lastTickMs = 0;
  private timerInterval: ReturnType<typeof setInterval> | null = null;

  private bars: number[] = Array(WAVEFORM_BAR_COUNT).fill(0.12);
  private barCursor = 0;
  private frameCounter = 0;
  private quietFrames = 0;
  private callbacks: PristineRecorderCallbacks;

  constructor(callbacks: PristineRecorderCallbacks) {
    this.callbacks = callbacks;
  }

  async start(deviceId?: string): Promise<void> {
    this.cleanupResources();
    this.chunks = [];
    this.finalTranscript = "";
    this.interimTranscript = "";
    this.activeSeconds = 0;
    this.barCursor = 0;
    this.quietFrames = 0;
    this.bars = Array(WAVEFORM_BAR_COUNT).fill(0.1);

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      const msg = "Microphone access requires a modern browser (Chrome, Edge, Safari, or Firefox) over localhost or HTTPS.";
      this.callbacks.onError(msg);
      this.callbacks.onMicHealth(msg, "error");
      throw new Error(msg);
    }

    const audioConstraints: MediaTrackConstraints = {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
      sampleRate: 48000,
      ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
    };

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
    } catch {
      // Fallback with minimal constraints if hardware rejects 48kHz/channelCount
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: deviceId ? { deviceId: { ideal: deviceId } } : true,
      });
    }

    // Set up Web Audio API real-time amplitude analyser
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.audioCtx = new AudioCtx();
    const source = this.audioCtx.createMediaStreamSource(this.stream);
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.72;
    source.connect(this.analyser);

    // Set up high-bitrate MediaRecorder
    const mimeType = selectBestAudioMimeType();
    const options: MediaRecorderOptions = {
      ...(mimeType ? { mimeType } : {}),
      audioBitsPerSecond: 128000,
    };
    this.recorder = new MediaRecorder(this.stream, options);
    this.recorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) {
        this.chunks.push(ev.data);
      }
    };
    this.recorder.start(250);

    this.isRecording = true;
    this.isPaused = false;
    this.lastTickMs = performance.now();

    this.callbacks.onMicHealth("Your microphone is picking you up clearly", "good");
    this.startTimer();
    this.startWaveformLoop();
    this.startLiveSpeechRecognition();
  }

  pause(): void {
    if (!this.isRecording || this.isPaused) return;
    this.isPaused = true;
    if (this.recorder && this.recorder.state === "recording") {
      this.recorder.pause();
    }
    this.stopLiveSpeechRecognition();
    this.callbacks.onMicHealth("Recording paused. Take a breath and resume anytime.", "idle");
  }

  resume(): void {
    if (!this.isRecording || !this.isPaused) return;
    this.isPaused = false;
    this.lastTickMs = performance.now();
    if (this.recorder && this.recorder.state === "paused") {
      this.recorder.resume();
    }
    this.startLiveSpeechRecognition();
    this.callbacks.onMicHealth("Your microphone is picking you up clearly", "good");
  }

  async stop(): Promise<{
    blob: Blob;
    durationSeconds: number;
    liveTranscript: string;
  }> {
    this.isRecording = false;
    this.isPaused = false;
    this.stopTimer();
    this.stopWaveformLoop();
    // Allow 300ms for final SpeechRecognition events to flush before tearing down
    await new Promise((r) => setTimeout(r, 300));
    this.stopLiveSpeechRecognition();

    const combinedTranscript = `${this.finalTranscript} ${this.interimTranscript}`
      .replace(/\s+/g, " ")
      .trim();

    const blob = await new Promise<Blob>((resolve) => {
      if (!this.recorder || this.recorder.state === "inactive") {
        resolve(new Blob(this.chunks, { type: selectBestAudioMimeType() || "audio/webm" }));
        return;
      }
      const rec = this.recorder;
      rec.onstop = () => {
        const mime = rec.mimeType || selectBestAudioMimeType() || "audio/webm";
        resolve(new Blob(this.chunks, { type: mime }));
      };
      try {
        rec.requestData();
      } catch {
        // ignore if unsupported
      }
      rec.stop();
    });

    const duration = Math.max(this.activeSeconds, 1);
    this.cleanupResources();

    return {
      blob,
      durationSeconds: Number(duration.toFixed(1)),
      liveTranscript: combinedTranscript,
    };
  }

  abort(): void {
    this.isRecording = false;
    this.isPaused = false;
    this.stopTimer();
    this.stopWaveformLoop();
    this.stopLiveSpeechRecognition();
    if (this.recorder && this.recorder.state !== "inactive") {
      try {
        this.recorder.stop();
      } catch {
        // ignore
      }
    }
    this.cleanupResources();
  }

  private startTimer(): void {
    this.stopTimer();
    this.timerInterval = setInterval(() => {
      if (!this.isRecording || this.isPaused) return;
      const now = performance.now();
      const deltaSec = (now - this.lastTickMs) / 1000;
      this.lastTickMs = now;
      this.activeSeconds += deltaSec;
      this.callbacks.onDurationTick(this.activeSeconds);
    }, 200);
  }

  private stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private startWaveformLoop(): void {
    this.stopWaveformLoop();
    const timeData = new Uint8Array(this.analyser ? this.analyser.fftSize : 256);

    const tick = () => {
      if (!this.isRecording) return;
      this.frameCounter += 1;

      if (!this.isPaused && this.analyser && this.frameCounter % 3 === 0) {
        this.analyser.getByteTimeDomainData(timeData);
        let sumSq = 0;
        for (let i = 0; i < timeData.length; i += 1) {
          const centered = (timeData[i] - 128) / 128;
          sumSq += centered * centered;
        }
        const rms = Math.sqrt(sumSq / timeData.length);
        // Perceptually scaled bar height between 0.10 and 1.0
        const normalized = Math.min(1, Math.max(0.1, rms * 5.2));

        // Update rolling visual waveform matching the Figma aesthetic
        if (this.barCursor < WAVEFORM_BAR_COUNT - 12) {
          this.bars[this.barCursor] = normalized;
          this.barCursor += 1;
        } else {
          // Shift window left so active edge sits cleanly around bar ~60 (matching Figma)
          const activeSplit = 60;
          for (let i = 0; i < activeSplit - 1; i += 1) {
            this.bars[i] = this.bars[i + 1];
          }
          this.bars[activeSplit - 1] = normalized;
          this.barCursor = activeSplit;
        }

        // Subtle ambient preview bars ahead of cursor
        for (let j = this.barCursor; j < WAVEFORM_BAR_COUNT; j += 1) {
          this.bars[j] = 0.14 + Math.abs(Math.sin(j * 0.65 + this.frameCounter * 0.03)) * 0.42;
        }

        if (rms < 0.006) {
          this.quietFrames += 1;
          if (this.quietFrames > 45) {
            this.callbacks.onMicHealth("Speak a little closer, your mic level is very quiet", "quiet");
          }
        } else {
          if (this.quietFrames > 45) {
            this.callbacks.onMicHealth("Your microphone is picking you up clearly", "good");
          }
          this.quietFrames = 0;
        }

        this.callbacks.onWaveform([...this.bars], this.barCursor);
      }

      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  private stopWaveformLoop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private startLiveSpeechRecognition(): void {
    if (typeof window === "undefined") return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    try {
      const rec = new SR();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";

      rec.onresult = (event: SpeechRecognitionEventLike) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const seg = event.results[i][0]?.transcript || "";
          if (event.results[i].isFinal) {
            this.finalTranscript = `${this.finalTranscript} ${seg}`.replace(/\s+/g, " ").trim();
          } else {
            interim += seg;
          }
        }
        this.interimTranscript = interim.trim();
        this.callbacks.onLiveTranscript(this.finalTranscript, this.interimTranscript);
      };

      rec.onerror = (ev) => {
        // Ignore non-fatal no-speech / aborted events while recording
        if (ev.error === "not-allowed") {
          this.callbacks.onError("Microphone permission denied for speech transcription.");
        }
      };

      rec.onend = () => {
        // Chrome automatically stops Web Speech after ~60s or silence: seamlessly restart while recording
        if (this.isRecording && !this.isPaused) {
          setTimeout(() => {
            if (this.isRecording && !this.isPaused) {
              this.startLiveSpeechRecognition();
            }
          }, 150);
        }
      };

      this.recognition = rec;
      rec.start();
    } catch {
      // Browser does not support concurrent SpeechRecognition; backend STT still transcribes audio blob
    }
  }

  private stopLiveSpeechRecognition(): void {
    if (this.recognition) {
      try {
        this.recognition.onend = null;
        this.recognition.stop();
      } catch {
        // ignore
      }
      this.recognition = null;
    }
  }

  private cleanupResources(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.audioCtx) {
      this.audioCtx.close().catch(() => {});
      this.audioCtx = null;
    }
    this.analyser = null;
    this.recorder = null;
  }
}

let activeAudioElement: HTMLAudioElement | null = null;

export async function speakQuestionAloud(
  text: string,
  onStart?: () => void,
  onEnd?: () => void
): Promise<void> {
  stopSpeakingQuestion();

  // Try neural TTS from backend first (ElevenLabs / OpenAI TTS if configured)
  const blob = await fetchNeuralTTS(text);
  if (blob) {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    activeAudioElement = audio;
    audio.onplay = () => onStart?.();
    audio.onended = () => {
      URL.revokeObjectURL(url);
      activeAudioElement = null;
      onEnd?.();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      activeAudioElement = null;
      onEnd?.();
    };
    await audio.play();
    return;
  }

  // Crisp Browser Web Speech API fallback (MVP standard)
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.98;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const preferred =
      voices.find((v) => /google us english|samantha|natural|aria|jenny/i.test(v.name)) ||
      voices.find((v) => v.lang.startsWith("en"));
    if (preferred) utterance.voice = preferred;

    utterance.onstart = () => onStart?.();
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();
    window.speechSynthesis.speak(utterance);
  }
}

export function stopSpeakingQuestion(): void {
  if (activeAudioElement) {
    activeAudioElement.pause();
    activeAudioElement = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}
