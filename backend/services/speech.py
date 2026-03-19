from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import torch
from faster_whisper import WhisperModel


class SpeechService:
    _model: WhisperModel | None = None
    _model_lock = Lock()
    _transcribe_lock = Lock()

    def __init__(self, model_size: str | None = None, device: str | None = None) -> None:
        self.device = self._resolve_device(device or os.getenv("WHISPER_DEVICE", "auto"))
        self.model_size = model_size or os.getenv(
            "WHISPER_MODEL_SIZE",
            "base" if self.device == "cuda" else "tiny.en",
        )
        default_compute_type = "float16" if self.device == "cuda" else "int8"
        self.compute_type = os.getenv("WHISPER_COMPUTE_TYPE", default_compute_type)
        self.cpu_threads = int(os.getenv("WHISPER_CPU_THREADS", "4"))
        self.num_workers = int(os.getenv("WHISPER_NUM_WORKERS", "1"))
        self.vad_filter = os.getenv("WHISPER_VAD_FILTER", "1") != "0"
        self.vad_min_silence_ms = int(os.getenv("WHISPER_VAD_MIN_SILENCE_MS", "400"))
        self.model = self._get_model()

    def preload(self) -> WhisperModel:
        return self.model

    def transcribe_file(self, audio_path: Path, prompt: str | None = None) -> str:
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            return ""

        try:
            with self._transcribe_lock:
                segments, _ = self.model.transcribe(
                    str(audio_path),
                    beam_size=1,
                    best_of=1,
                    language="en",
                    condition_on_previous_text=False,
                    initial_prompt=prompt or "Live lecture transcription with technical terms.",
                    vad_filter=self.vad_filter,
                    vad_parameters={"min_silence_duration_ms": self.vad_min_silence_ms},
                    temperature=0.0,
                )
                text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        except Exception:
            return ""

        return " ".join(text.split()).strip()

    def _get_model(self) -> WhisperModel:
        if self.__class__._model is None:
            with self.__class__._model_lock:
                if self.__class__._model is None:
                    self.__class__._model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                        cpu_threads=self.cpu_threads,
                        num_workers=self.num_workers,
                    )
        return self.__class__._model

    def _resolve_device(self, requested_device: str) -> str:
        device = requested_device.strip().lower()
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            return "cpu"
        return device if device in {"cpu", "cuda"} else "cpu"
