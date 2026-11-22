from __future__ import annotations

import re
from collections import Counter
from typing import Any

from models.schemas import AwkwardPause, DeliveryMetrics, WordTimestamp

SINGLE_WORD_FILLERS = {
    "um", "umm", "ummm", "uh", "uhh", "uhhh", "uhm", "er", "erm", "ah", "ahh", "hmm",
    "basically", "literally", "actually",
}

PHRASE_FILLERS = [
    "you know",
    "i mean",
    "sort of",
    "kind of",
]

# Contextual check for "like" so "looks like" / "would like" isn't over-penalized
NON_FILLER_LIKE_BEFORE = {"would", "looks", "look", "feels", "feel", "seems", "seem", "sounds", "sound", "something", "anything", "nothing", "things", "more", "just"}

HEDGING_PATTERNS = [
    r"\bi think maybe\b",
    r"\bi'?m not really sure\b",
    r"\bi'?m not sure(?:,?\s+but)?\b",
    r"\bi guess\b",
    r"\bmaybe we could\b",
    r"\bprobably maybe\b",
    r"\bi might be wrong\b",
    r"\bcorrect me if i'?m wrong\b",
    r"\bhonestly i don'?t know\b",
    r"\bkind of maybe\b",
    r"\bi suppose\b",
    r"\bif that makes sense\b",
    r"\bhopefully\b",
]


def format_mm_ss(seconds: float) -> str:
    sec = max(0, int(round(seconds)))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"


def clean_word(token: str) -> str:
    return re.sub(r"[^a-zA-Z0-9']", "", token).lower()


def analyze_delivery_signals(
    transcript_verbatim: str,
    duration_seconds: float,
    word_timestamps: list[WordTimestamp] | None = None,
    stt_provider: str = "browser_live",
) -> DeliveryMetrics:
    text = (transcript_verbatim or "").strip()
    raw_tokens = re.findall(r"[A-Za-z0-9']+|[.,!?;:]", text)
    words_only = [t for t in raw_tokens if re.match(r"^[A-Za-z0-9']+$", t)]
    word_count = len(words_only)

    effective_duration = max(duration_seconds, 1.0)
    if duration_seconds <= 1.0 and word_timestamps and len(word_timestamps) >= 2:
        effective_duration = max(word_timestamps[-1].end - word_timestamps[0].start, 1.0)
    elif duration_seconds <= 1.0 and word_count > 0:
        effective_duration = max(word_count / 2.3, 5.0)

    minutes = max(effective_duration / 60.0, 0.05)
    wpm = int(round(word_count / minutes)) if word_count > 0 else 0

    # Pace rubric
    if wpm == 0:
        pace_label, pace_status = "No speech", "warn"
    elif wpm > 175:
        pace_label, pace_status = "Too fast", "warn"
    elif wpm > 165:
        pace_label, pace_status = "Brisk", "neutral"
    elif wpm >= 115:
        pace_label, pace_status = "Steady", "good"
    elif wpm >= 100:
        pace_label, pace_status = "Measured", "neutral"
    else:
        pace_label, pace_status = "Too slow", "warn"

    # Filler word detection (single-word + phrase + contextual "like")
    filler_counter: Counter[str] = Counter()
    lower_words = [w.lower() for w in words_only]

    for i, w in enumerate(lower_words):
        if w in SINGLE_WORD_FILLERS:
            canonical = "um" if w.startswith("um") else ("uh" if w.startswith("uh") else w)
            filler_counter[canonical] += 1
        elif w == "like":
            prev = lower_words[i - 1] if i > 0 else ""
            if prev not in NON_FILLER_LIKE_BEFORE:
                filler_counter["like"] += 1

    lower_text = text.lower()
    for phrase in PHRASE_FILLERS:
        matches = re.findall(rf"\b{re.escape(phrase)}\b", lower_text)
        if matches:
            filler_counter[phrase] += len(matches)

    total_fillers = sum(filler_counter.values())
    filler_per_min = round(total_fillers / minutes, 1) if word_count > 0 else 0.0

    if filler_per_min <= 2.0:
        filler_label, filler_status = "Clean", "good"
    elif filler_per_min <= 4.0:
        filler_label, filler_status = "Moderate", "neutral"
    else:
        filler_label, filler_status = "Reduce", "warn"

    # Pause analysis using word-level timestamps
    awkward_pauses: list[AwkwardPause] = []
    longest_pause = 0.0
    has_word_timestamps = bool(word_timestamps and len(word_timestamps) >= 2)

    if has_word_timestamps and word_timestamps:
        for i in range(1, len(word_timestamps)):
            prev_w = word_timestamps[i - 1]
            curr_w = word_timestamps[i]
            gap = round(max(0.0, curr_w.start - prev_w.end), 2)
            if gap > longest_pause:
                longest_pause = gap
            if gap >= 2.5:
                awkward_pauses.append(
                    AwkwardPause(
                        start_sec=round(prev_w.end, 2),
                        end_sec=round(curr_w.start, 2),
                        duration_sec=gap,
                        before_word=prev_w.word,
                        after_word=curr_w.word,
                    )
                )
    else:
        # Estimate longest pause conservatively from punctuation/ellipses if no timestamps exist
        if "..." in text or "—" in text:
            longest_pause = 2.6
        elif word_count > 0:
            longest_pause = round(min(2.2, max(0.6, (effective_duration / max(word_count, 1)) * 2.1)), 1)

    if longest_pause >= 2.5:
        pause_label, pause_status = "Noticeable", "warn"
    elif longest_pause >= 1.6:
        pause_label, pause_status = "Brief", "neutral"
    else:
        pause_label, pause_status = "Smooth", "good"

    # Hedging language scan
    hedging_found: list[str] = []
    for pat in HEDGING_PATTERNS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            snippet = m.group(0).strip()
            if snippet.lower() not in {h.lower() for h in hedging_found}:
                hedging_found.append(snippet)

    # Build annotated transcript with inline [pause X.Xs] markers for LLM & transcript drawer
    annotated = text
    if has_word_timestamps and word_timestamps:
        parts: list[str] = []
        for idx, wt in enumerate(word_timestamps):
            if idx > 0:
                gap = wt.start - word_timestamps[idx - 1].end
                if gap >= 2.5:
                    parts.append(f"[pause {gap:.1f}s]")
            parts.append(wt.word)
        annotated = " ".join(parts)

    return DeliveryMetrics(
        duration_seconds=round(effective_duration, 1),
        duration_formatted=format_mm_ss(effective_duration),
        word_count=word_count,
        speaking_pace_wpm=wpm,
        pace_label=pace_label,
        pace_status=pace_status,
        filler_count=total_fillers,
        filler_per_min=filler_per_min,
        filler_label=filler_label,
        filler_status=filler_status,
        filler_breakdown=dict(filler_counter),
        longest_pause_sec=round(longest_pause, 1),
        pause_label=pause_label,
        pause_status=pause_status,
        awkward_pauses=awkward_pauses,
        hedging_phrases=hedging_found,
        annotated_transcript=annotated,
        stt_provider=stt_provider,
        has_word_timestamps=has_word_timestamps,
    )


def strip_fillers_for_clean_transcript(verbatim: str) -> str:
    cleaned = re.sub(r"\b(um+|uh+|uhm|erm|hmm)\b[,\s]*", "", verbatim, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned
