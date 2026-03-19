from __future__ import annotations

import os
import re
from threading import Lock

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class TranslateService:
    _model = None
    _tokenizer = None
    _model_lock = Lock()
    _run_lock = Lock()

    def __init__(self) -> None:
        self.model_name = os.getenv("TRANSLATION_MODEL_NAME", "facebook/m2m100_418M")
        self.device = self._resolve_device(os.getenv("TRANSLATION_DEVICE", "auto"))
        self.max_length = int(os.getenv("TRANSLATION_MAX_LENGTH", "192"))
        self.num_beams = int(os.getenv("TRANSLATION_NUM_BEAMS", "1"))
        self.model_family = "nllb" if "nllb" in self.model_name.lower() else "m2m100"
        if self.model_family == "nllb":
            self.supported_languages = {"hi": "hin_Deva", "ta": "tam_Taml"}
            self.source_language = "eng_Latn"
        else:
            self.supported_languages = {"hi": "hi", "ta": "ta"}
            self.source_language = "en"

    def preload(self):
        return self._get_model_bundle()

    def translate_text(self, text: str, target_language: str) -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        target_code = self.supported_languages.get(target_language, self.supported_languages["hi"])

        try:
            tokenizer, model = self._get_model_bundle()
            translated_parts: list[str] = []

            for chunk in self._chunk_text(clean_text):
                if hasattr(tokenizer, "src_lang"):
                    tokenizer.src_lang = self.source_language

                encoded = tokenizer(
                    chunk,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                )
                encoded = {key: value.to(model.device) for key, value in encoded.items()}
                forced_bos_token_id = self._target_token_id(tokenizer, target_code)

                with self._run_lock:
                    with torch.no_grad():
                        generated = model.generate(
                            **encoded,
                            forced_bos_token_id=forced_bos_token_id,
                            max_length=self.max_length,
                            num_beams=self.num_beams,
                            early_stopping=True,
                        )

                translated_parts.append(tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip())

            return " ".join(part for part in translated_parts if part).strip() or clean_text
        except Exception as exc:
            print(f"Translation failed for target={target_language}: {exc}")
            return clean_text

    def _get_model_bundle(self):
        if self.__class__._model is None or self.__class__._tokenizer is None:
            with self.__class__._model_lock:
                if self.__class__._model is None or self.__class__._tokenizer is None:
                    tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                    model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                    model.to(self.device)
                    model.eval()
                    self.__class__._tokenizer = tokenizer
                    self.__class__._model = model
        return self.__class__._tokenizer, self.__class__._model

    def _target_token_id(self, tokenizer, target_code: str) -> int:
        if hasattr(tokenizer, "get_lang_id"):
            return tokenizer.get_lang_id(target_code)
        if hasattr(tokenizer, "lang_code_to_id") and target_code in tokenizer.lang_code_to_id:
            return tokenizer.lang_code_to_id[target_code]
        token_id = tokenizer.convert_tokens_to_ids(target_code)
        if token_id is None:
            raise RuntimeError(f"Unsupported target language token: {target_code}")
        return token_id

    def _resolve_device(self, requested_device: str) -> str:
        device = requested_device.strip().lower()
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            return "cpu"
        return device if device in {"cpu", "cuda"} else "cpu"

    def _chunk_text(self, text: str, max_chars: int = 280) -> list[str]:
        if len(text) <= max_chars:
            return [text]

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_chars:
                current = f"{current} {sentence}".strip()
                continue

            if current:
                chunks.append(current)
            current = sentence

        if current:
            chunks.append(current)

        return chunks
