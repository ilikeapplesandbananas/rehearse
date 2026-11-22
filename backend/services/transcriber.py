from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx

from config import settings
from models.schemas import WordTimestamp
from services.delivery_metrics import SINGLE_WORD_FILLERS, clean_word, strip_fillers_for_clean_transcript

logger = logging.getLogger(__name__)

VERBATIM_WHISPER_PROMPT = (
    "Umm, uh, like, you know, so basically, let me think about how we scaled "
    "the system architecture, PostgreSQL, Redis, Kubernetes, microservices, API."
)


def _normalize_audio_mime(content_type: str) -> str:
    base = (content_type or "audio/webm").split(";")[0].strip().lower()
    if base in {"audio/webm", "audio/mp4", "audio/ogg", "audio/wav", "audio/mpeg", "audio/mp3", "audio/aac"}:
        return base
    if "mp4" in base or "m4a" in base:
        return "audio/mp4"
    if "ogg" in base:
        return "audio/ogg"
    if "wav" in base:
        return "audio/wav"
    return "audio/webm"


def _build_synthetic_timestamps_from_pauses(
    annotated_text: str, duration_seconds: float
) -> tuple[str, list[WordTimestamp]]:
    """
    Converts Gemini verbatim output containing optional '[pause 3.1s]' tags into
    clean verbatim text + synthetic WordTimestamp sequence so pause/WPM telemetry works seamlessly.
    """
    tokens = re.split(r"(\[pause\s+\d+(?:\.\d+)?s\])", annotated_text, flags=re.I)
    pause_events: list[tuple[int, float]] = []
    plain_words: list[str] = []

    for chunk in tokens:
        chunk = chunk.strip()
        if not chunk:
            continue
        pm = re.match(r"^\[pause\s+(\d+(?:\.\d+)?)s\]$", chunk, flags=re.I)
        if pm:
            pause_events.append((len(plain_words), float(pm.group(1))))
        else:
            for w in chunk.split():
                plain_words.append(w)

    verbatim = " ".join(plain_words).strip()
    if not plain_words or not pause_events:
        return verbatim, []

    total_pause_sec = sum(p for _, p in pause_events)
    eff_dur = max(duration_seconds, total_pause_sec + len(plain_words) * 0.35)
    speech_dur = max(1.0, eff_dur - total_pause_sec)
    step = speech_dur / len(plain_words)

    pause_map: dict[int, float] = {}
    for idx, p_sec in pause_events:
        pause_map[idx] = pause_map.get(idx, 0.0) + p_sec

    timestamps: list[WordTimestamp] = []
    cursor = 0.0
    for idx, word_str in enumerate(plain_words):
        if idx in pause_map:
            cursor += pause_map[idx]
        start = round(cursor, 3)
        end = round(cursor + max(0.12, step * 0.85), 3)
        timestamps.append(
            WordTimestamp(
                word=word_str,
                start=start,
                end=end,
                confidence=0.96,
                is_filler=clean_word(word_str) in SINGLE_WORD_FILLERS,
            )
        )
        cursor += step

    return verbatim, timestamps


async def transcribe_audio_bytes(
    audio_bytes: bytes,
    content_type: str = "audio/webm",
    filename: str = "answer.webm",
    fallback_transcript: str = "",
    duration_seconds: float = 0.0,
) -> dict[str, Any]:
    """
    Pristine multi-tier verbatim Speech-to-Text pipeline.
    Priority:
      1. Deepgram Nova-3 / Nova-2 (verbatim filler_words=true + word-level timestamps)
      2. OpenAI Whisper (verbose_json + word timestamps + disfluency-preserving prompt)
      3. Groq Whisper Large-v3-Turbo (verbose_json + word timestamps)
      4. Gemini Multimodal Audio STT (gemini-3.5-transcribe / gemini-3.1-flash-lite)
      5. Client live transcript fallback (when offline or typed)
    """
    has_audio = bool(audio_bytes and len(audio_bytes) > 600)

    # Tier 1: Deepgram Nova-3 / Nova-2
    if has_audio and settings.deepgram_api_key:
        try:
            return await _transcribe_deepgram(audio_bytes, content_type)
        except Exception as exc:
            logger.warning("Deepgram transcription failed, falling back: %s", exc)

    # Tier 2: OpenAI Whisper
    if has_audio and settings.openai_api_key:
        try:
            return await _transcribe_openai_whisper(audio_bytes, content_type, filename)
        except Exception as exc:
            logger.warning("OpenAI Whisper transcription failed, falling back: %s", exc)

    # Tier 3: Groq Whisper
    if has_audio and settings.groq_api_key:
        try:
            return await _transcribe_groq_whisper(audio_bytes, content_type, filename)
        except Exception as exc:
            logger.warning("Groq Whisper transcription failed, falling back: %s", exc)

    # Tier 4: Gemini Multimodal Audio Verbatim Transcriber
    if has_audio and settings.gemini_api_key:
        try:
            res = await _transcribe_gemini_audio(
                audio_bytes=audio_bytes,
                content_type=content_type,
                fallback_transcript=fallback_transcript,
                duration_seconds=duration_seconds,
            )
            if res["transcript_verbatim"]:
                return res
        except Exception as exc:
            logger.warning("Gemini audio transcription failed, falling back: %s", exc)

    # Tier 5: Live browser transcript fallback
    verbatim = (fallback_transcript or "").replace("\u2014", ", ").replace("\u2013", "-").strip()
    return {
        "stt_provider": "browser_live",
        "transcript_verbatim": verbatim,
        "transcript_clean": strip_fillers_for_clean_transcript(verbatim),
        "word_timestamps": [],
        "duration_seconds": duration_seconds,
    }


async def _transcribe_gemini_audio(
    audio_bytes: bytes,
    content_type: str,
    fallback_transcript: str,
    duration_seconds: float,
) -> dict[str, Any]:
    mime_type = _normalize_audio_mime(content_type)
    b64_audio = base64.b64encode(audio_bytes).decode("ascii")
    prompt = (
        "Transcribe the spoken audio verbatim for an interview coach. "
        "Keep EVERY spoken word and filler disfluency exactly as spoken (um, uh, like, you know, basically, actually). "
        "Do NOT fix grammar or paraphrase. Do NOT use em dashes or en dashes. "
        "Whenever there is a clear mid-sentence silence or hesitation pause lasting 2.5 seconds or longer, "
        "insert [pause X.Xs] inline (for example [pause 3.1s]). "
        "Return ONLY the verbatim transcript text and nothing else."
    )

    models_to_try = ["gemini-3.5-transcribe", "gemini-3.1-flash-lite"]
    raw_text = ""
    used_model = "gemini-3.5-transcribe"

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inlineData": {"mimeType": mime_type, "data": b64_audio}},
                        ],
                    }
                ],
                "generationConfig": {"temperature": 0.0},
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
                if r.status_code >= 400:
                    continue
                data = r.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            candidate_txt = "".join(p.get("text", "") for p in parts if "text" in p).strip()
            if candidate_txt:
                raw_text = candidate_txt
                used_model = model_name
                break
        except Exception as exc:
            logger.debug("Gemini STT model %s failed: %s", model_name, exc)

    if not raw_text:
        raw_text = (fallback_transcript or "").strip()

    raw_text = raw_text.replace("\u2014", ", ").replace("\u2013", "-").strip()
    verbatim, timestamps = _build_synthetic_timestamps_from_pauses(raw_text, duration_seconds)
    if not verbatim:
        verbatim = (fallback_transcript or "").strip()

    return {
        "stt_provider": f"gemini:{used_model}",
        "transcript_verbatim": verbatim,
        "transcript_clean": strip_fillers_for_clean_transcript(verbatim),
        "word_timestamps": timestamps,
        "duration_seconds": duration_seconds,
    }


async def _transcribe_deepgram(audio_bytes: bytes, content_type: str) -> dict[str, Any]:
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": settings.deepgram_model or "nova-3",
        "smart_format": "true",
        "punctuate": "true",
        "filler_words": "true",
        "utterances": "true",
        "diarize": "false",
    }
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": content_type or "audio/webm",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, params=params, headers=headers, content=audio_bytes)
        if resp.status_code >= 400 and params["model"] != "nova-2":
            params["model"] = "nova-2"
            resp = await client.post(url, params=params, headers=headers, content=audio_bytes)
        resp.raise_for_status()
        data = resp.json()

    channels = data.get("results", {}).get("channels", [])
    alt = channels[0]["alternatives"][0] if channels and channels[0].get("alternatives") else {}
    verbatim = alt.get("transcript", "").strip()
    raw_words = alt.get("words", [])
    duration = float(data.get("metadata", {}).get("duration", 0.0) or 0.0)

    timestamps: list[WordTimestamp] = []
    for w in raw_words:
        word_str = str(w.get("punctuated_word") or w.get("word") or "").strip()
        if not word_str:
            continue
        timestamps.append(
            WordTimestamp(
                word=word_str,
                start=round(float(w.get("start", 0.0)), 3),
                end=round(float(w.get("end", 0.0)), 3),
                confidence=round(float(w.get("confidence", 0.99)), 3),
                is_filler=clean_word(word_str) in SINGLE_WORD_FILLERS,
            )
        )

    return {
        "stt_provider": f"deepgram:{params['model']}",
        "transcript_verbatim": verbatim,
        "transcript_clean": strip_fillers_for_clean_transcript(verbatim),
        "word_timestamps": timestamps,
        "duration_seconds": duration,
    }


async def _transcribe_openai_whisper(
    audio_bytes: bytes, content_type: str, filename: str
) -> dict[str, Any]:
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {"file": (filename or "answer.webm", audio_bytes, content_type or "audio/webm")}
    data = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "prompt": VERBATIM_WHISPER_PROMPT,
        "timestamp_granularities[]": "word",
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        resp.raise_for_status()
        payload = resp.json()

    verbatim = str(payload.get("text", "")).strip()
    duration = float(payload.get("duration", 0.0) or 0.0)
    raw_words = payload.get("words", [])
    timestamps: list[WordTimestamp] = [
        WordTimestamp(
            word=str(w.get("word", "")).strip(),
            start=round(float(w.get("start", 0.0)), 3),
            end=round(float(w.get("end", 0.0)), 3),
            confidence=0.98,
            is_filler=clean_word(str(w.get("word", ""))) in SINGLE_WORD_FILLERS,
        )
        for w in raw_words
        if str(w.get("word", "")).strip()
    ]

    return {
        "stt_provider": "openai:whisper-1",
        "transcript_verbatim": verbatim,
        "transcript_clean": strip_fillers_for_clean_transcript(verbatim),
        "word_timestamps": timestamps,
        "duration_seconds": duration,
    }


async def _transcribe_groq_whisper(
    audio_bytes: bytes, content_type: str, filename: str
) -> dict[str, Any]:
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    files = {"file": (filename or "answer.webm", audio_bytes, content_type or "audio/webm")}
    data = {
        "model": settings.groq_whisper_model or "whisper-large-v3-turbo",
        "response_format": "verbose_json",
        "prompt": VERBATIM_WHISPER_PROMPT,
        "timestamp_granularities[]": "word",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        resp.raise_for_status()
        payload = resp.json()

    verbatim = str(payload.get("text", "")).strip()
    duration = float(payload.get("duration", 0.0) or 0.0)
    raw_words = payload.get("words", [])
    timestamps: list[WordTimestamp] = [
        WordTimestamp(
            word=str(w.get("word", "")).strip(),
            start=round(float(w.get("start", 0.0)), 3),
            end=round(float(w.get("end", 0.0)), 3),
            confidence=0.97,
            is_filler=clean_word(str(w.get("word", ""))) in SINGLE_WORD_FILLERS,
        )
        for w in raw_words
        if str(w.get("word", "")).strip()
    ]

    return {
        "stt_provider": f"groq:{data['model']}",
        "transcript_verbatim": verbatim,
        "transcript_clean": strip_fillers_for_clean_transcript(verbatim),
        "word_timestamps": timestamps,
        "duration_seconds": duration,
    }


async def synthesize_speech_bytes(text: str) -> tuple[bytes | None, str]:
    """Optional high-quality neural TTS (ElevenLabs or OpenAI TTS)."""
    clean_text = text.strip()[:1200]
    if not clean_text:
        return (None, "")

    if settings.elevenlabs_api_key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
            headers = {
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            body = {
                "text": clean_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, headers=headers, json=body)
                r.raise_for_status()
                return (r.content, "audio/mpeg")
        except Exception as exc:
            logger.warning("ElevenLabs TTS failed: %s", exc)

    if settings.openai_api_key:
        try:
            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            }
            body = {"model": "tts-1", "voice": "alloy", "input": clean_text}
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, headers=headers, json=body)
                r.raise_for_status()
                return (r.content, "audio/mpeg")
        except Exception as exc:
            logger.warning("OpenAI TTS failed: %s", exc)

    return (None, "")
