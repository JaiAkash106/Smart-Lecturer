from __future__ import annotations

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from services.speech import SpeechService
from services.summarize import SummarizeService
from services.translate import TranslateService

load_dotenv()

ENABLE_BACKGROUND_WARMUP = os.getenv("ENABLE_BACKGROUND_WARMUP", "1") != "0"
LIVE_SUMMARY_MODE = os.getenv("LIVE_SUMMARY_MODE", "fast").strip().lower()
MIN_TRANSCRIPT_CHARS = int(os.getenv("MIN_TRANSCRIPT_CHARS", "3"))

app = FastAPI(title="Real-Time Multilingual Lecture Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

speech_service = SpeechService()
translate_service = TranslateService()
summarize_service = SummarizeService()


@dataclass
class LectureSession:
    original_text: str = ""
    translated_text: str = ""
    summary: str = ""
    keywords: list[str] = field(default_factory=list)

    def as_payload(self) -> dict[str, Any]:
        return {
            "original": self.original_text,
            "translated": self.translated_text,
            "summary": self.summary,
            "keywords": self.keywords,
        }


async def _warmup_models() -> None:
    try:
        await asyncio.to_thread(speech_service.preload)
        await asyncio.to_thread(translate_service.preload)
        await asyncio.to_thread(summarize_service.preload)
        print("Background model warmup complete.")
    except Exception as exc:
        print(f"Background model warmup skipped: {exc}")


@app.on_event("startup")
async def startup_event() -> None:
    if ENABLE_BACKGROUND_WARMUP:
        asyncio.create_task(_warmup_models())


def _normalize_language(raw_language: str | None) -> str:
    language = (raw_language or "hi").strip().lower()
    if language not in {"hi", "ta"}:
        return "hi"
    return language


def _save_temp_audio(audio_bytes: bytes, suffix: str = ".webm") -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(audio_bytes)
        return Path(temp_file.name)


def _suffix_from_name(filename: str | None) -> str:
    if not filename:
        return ".webm"
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ".webm"


def _merge_text(existing: str, incoming: str, max_overlap_words: int = 12) -> str:
    current = " ".join(existing.split()).strip()
    new_text = " ".join(incoming.split()).strip()

    if not current:
        return new_text
    if not new_text:
        return current
    if new_text.lower() in current.lower():
        return current

    current_words = current.split()
    incoming_words = new_text.split()
    overlap_limit = min(max_overlap_words, len(current_words), len(incoming_words))

    for size in range(overlap_limit, 0, -1):
        current_tail = " ".join(current_words[-size:]).lower()
        incoming_head = " ".join(incoming_words[:size]).lower()
        if current_tail == incoming_head:
            merged = current_words + incoming_words[size:]
            return " ".join(merged).strip()

    return f"{current} {new_text}".strip()


def _is_useful_transcript(transcript: str) -> bool:
    return len(transcript.strip()) >= MIN_TRANSCRIPT_CHARS


async def _build_live_insights(text: str) -> tuple[str, list[str]]:
    summary_fn = summarize_service.quick_summary_text if LIVE_SUMMARY_MODE == "fast" else summarize_service.summarize_text
    summary_task = asyncio.to_thread(summary_fn, text)
    keywords_task = asyncio.to_thread(summarize_service.extract_keywords, text)
    summary, keywords = await asyncio.gather(summary_task, keywords_task)
    return summary, keywords


async def _process_transcript_chunk(
    audio_path: Path,
    target_language: str,
    session: LectureSession,
) -> dict[str, Any] | None:
    prompt = f"Previous lecture context: {session.original_text[-160:]}"
    try:
        transcript = await asyncio.to_thread(
            speech_service.transcribe_file,
            audio_path,
            prompt,
        )
    finally:
        audio_path.unlink(missing_ok=True)

    if not transcript or not _is_useful_transcript(transcript):
        return None

    merged_original = _merge_text(session.original_text, transcript)
    translation_task = asyncio.to_thread(translate_service.translate_text, transcript, target_language)
    insights_task = _build_live_insights(merged_original)
    translated, (summary, keywords) = await asyncio.gather(translation_task, insights_task)

    session.original_text = merged_original
    session.translated_text = _merge_text(session.translated_text, translated)
    session.summary = summary
    session.keywords = keywords
    return session.as_payload()


async def _process_uploaded_file(audio_path: Path, target_language: str) -> dict[str, Any]:
    try:
        transcript = await asyncio.to_thread(speech_service.transcribe_file, audio_path, None)
    finally:
        audio_path.unlink(missing_ok=True)

    if not transcript:
        return {
            "original": "",
            "translated": "",
            "summary": "No speech detected in the uploaded file.",
            "keywords": [],
        }

    translation_task = asyncio.to_thread(translate_service.translate_text, transcript, target_language)
    summary_task = asyncio.to_thread(summarize_service.summarize_text, transcript)
    keywords_task = asyncio.to_thread(summarize_service.extract_keywords, transcript)
    translated, summary, keywords = await asyncio.gather(translation_task, summary_task, keywords_task)
    return {
        "original": transcript,
        "translated": translated,
        "summary": summary,
        "keywords": keywords,
    }


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "whisper_device": speech_service.device,
        "whisper_model": speech_service.model_size,
        "translation_device": translate_service.device,
        "translation_model": translate_service.model_name,
        "summary_device": summarize_service.device,
        "summary_model": summarize_service.model_name,
        "live_summary_mode": LIVE_SUMMARY_MODE,
    }


@app.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    target_language: str = Form("hi"),
) -> dict[str, Any]:
    target_language = _normalize_language(target_language)
    audio_bytes = await file.read()
    audio_path = _save_temp_audio(audio_bytes, suffix=_suffix_from_name(file.filename))

    try:
        return await _process_uploaded_file(audio_path, target_language)
    except Exception as exc:
        return {
            "original": "",
            "translated": "",
            "summary": "Processing failed for the uploaded audio.",
            "keywords": [],
            "error": str(exc),
        }


@app.websocket("/ws/lecture")
async def lecture_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    session = LectureSession()
    target_language = _normalize_language(websocket.query_params.get("target_language"))

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if message.get("text"):
                payload = json.loads(message["text"])
                if payload.get("type") == "set_language":
                    target_language = _normalize_language(payload.get("target_language"))
                    await websocket.send_json(
                        {
                            **session.as_payload(),
                            "info": f"Translation language switched to {target_language}.",
                        }
                    )
                continue

            audio_bytes = message.get("bytes")
            if not audio_bytes:
                continue

            audio_path = _save_temp_audio(audio_bytes)
            try:
                payload = await _process_transcript_chunk(audio_path, target_language, session)
                if payload:
                    await websocket.send_json(payload)
            except Exception as exc:
                await websocket.send_json(
                    {
                        **session.as_payload(),
                        "error": f"Chunk processing failed: {exc}",
                    }
                )
    except WebSocketDisconnect:
        return
