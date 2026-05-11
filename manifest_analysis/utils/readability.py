"""Reusable readability and patch-text helpers."""

from __future__ import annotations

import math
import re
from typing import Optional

import textstat


class ReadabilityMetrics:
    """Shared helpers for word counts and Flesch-style scoring."""

    CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    WORD_RE = re.compile(r"\b\w+\b")

    @classmethod
    def strip_code_blocks(cls, text: Optional[str]) -> str:
        if not text:
            return ""
        return cls.CODE_BLOCK_RE.sub("", text)

    @classmethod
    def extract_patch_lines(cls, patch_content: Optional[str], line_prefix: str) -> str:
        if not patch_content:
            return ""

        lines = []
        for line in patch_content.splitlines():
            if line.startswith("@@"):
                continue
            if line.startswith(line_prefix) and not line.startswith("+++") and not line.startswith("---"):
                content = line[1:].strip()
                if content:
                    lines.append(content)
        return "\n".join(lines)

    @classmethod
    def calculate_length_of_words(cls, text: Optional[str]) -> int:
        if not text:
            return 0
        text_without_code = cls.strip_code_blocks(text)
        return len(cls.WORD_RE.findall(text_without_code))

    @classmethod
    def calculate_complexity_score(cls, text: Optional[str]) -> float:
        if not text or len(text.strip()) < 10:
            return 0.0

        cleaned = cls.strip_code_blocks(text).strip()
        if len(cleaned) < 10:
            return 0.0

        try:
            score = textstat.flesch_reading_ease(cleaned)
        except Exception:
            return 0.0

        if score is None or math.isnan(score):
            return 0.0
        return round(float(score), 2)

    @classmethod
    def commit_patch_metrics(cls, patch_content: Optional[str]) -> dict[str, float | int]:
        deleted_text = cls.extract_patch_lines(patch_content, "-")
        added_text = cls.extract_patch_lines(patch_content, "+")
        return {
            "del_lines_of_words": cls.calculate_length_of_words(deleted_text),
            "del_complexity_score": cls.calculate_complexity_score(deleted_text),
            "add_lines_of_words": cls.calculate_length_of_words(added_text),
            "add_complexity_score": cls.calculate_complexity_score(added_text),
        }

    @staticmethod
    def create_file_key(owner: Optional[str], repo: Optional[str], file_url: Optional[str]) -> str:
        return f"{owner or ''}||{repo or ''}||{file_url or ''}"

