from __future__ import annotations

import os
import re
from collections import Counter
from threading import Lock

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}


class SummarizeService:
    _model = None
    _tokenizer = None
    _model_lock = Lock()
    _run_lock = Lock()

    def __init__(self) -> None:
        self.model_name = os.getenv("SUMMARY_MODEL_NAME", "sshleifer/distilbart-cnn-12-6")
        self.device = self._resolve_device(os.getenv("SUMMARY_DEVICE", "auto"))
        self.abstractive_min_words = int(os.getenv("SUMMARY_ABSTRACTIVE_MIN_WORDS", "90"))
        self.max_input_words = int(os.getenv("SUMMARY_MAX_INPUT_WORDS", "180"))

    def preload(self):
        return self._get_model_bundle()

    def quick_summary_text(self, text: str) -> str:
        clean_text = self._normalize(text)
        if not clean_text:
            return "Start speaking to generate a simplified explanation."
        return self._extractive_summary(clean_text)

    def summarize_text(self, text: str) -> str:
        clean_text = self._normalize(text)
        if not clean_text:
            return "Start speaking to generate a simplified explanation."

        word_count = len(clean_text.split())
        if word_count < self.abstractive_min_words:
            return self._extractive_summary(clean_text)

        try:
            tokenizer, model = self._get_model_bundle()
            trimmed_text = " ".join(clean_text.split()[-self.max_input_words:])
            encoded = tokenizer(
                trimmed_text,
                max_length=768,
                truncation=True,
                return_tensors="pt",
            )
            encoded = {key: value.to(model.device) for key, value in encoded.items()}

            max_length = max(36, min(96, len(trimmed_text.split()) // 2))
            min_length = max(16, min(48, max_length // 2))

            with self._run_lock:
                with torch.no_grad():
                    summary_ids = model.generate(
                        **encoded,
                        max_length=max_length,
                        min_length=min_length,
                        num_beams=1,
                        early_stopping=True,
                        no_repeat_ngram_size=2,
                    )

            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()
            return summary or self._extractive_summary(clean_text)
        except Exception:
            return self._extractive_summary(clean_text)

    def extract_keywords(self, text: str, limit: int = 6) -> list[str]:
        clean_text = self._normalize(text).lower()
        if not clean_text:
            return []

        words = [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", clean_text)
            if token not in STOPWORDS
        ]
        frequencies = Counter(words)
        return [word for word, _ in frequencies.most_common(limit)]

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

    def _resolve_device(self, requested_device: str) -> str:
        device = requested_device.strip().lower()
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            return "cpu"
        return device if device in {"cpu", "cuda"} else "cpu"

    def _extractive_summary(self, text: str, sentence_limit: int = 2) -> str:
        sentences = self._split_sentences(text)
        if len(sentences) <= sentence_limit:
            return text

        word_scores = self._word_scores(text)
        ranked_sentences = sorted(
            sentences,
            key=lambda sentence: self._sentence_score(sentence, word_scores),
            reverse=True,
        )
        selected = ranked_sentences[:sentence_limit]
        ordered = [sentence for sentence in sentences if sentence in selected]
        summary = " ".join(ordered).strip()
        return summary[:420]

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _split_sentences(self, text: str) -> list[str]:
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]

    def _word_scores(self, text: str) -> Counter[str]:
        words = [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
            if token not in STOPWORDS
        ]
        return Counter(words)

    def _sentence_score(self, sentence: str, word_scores: Counter[str]) -> float:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", sentence.lower())
        if not words:
            return 0.0

        score = sum(word_scores.get(word, 0) for word in words if word not in STOPWORDS)
        return score / len(words)
