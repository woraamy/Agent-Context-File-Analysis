"""Shared code-metric helpers backed by Lizard and simple patch parsing."""

from __future__ import annotations

import os
import re
import signal
from contextlib import contextmanager
from typing import Iterator

import lizard
from radon.complexity import cc_visit
from radon.raw import analyze


class _TimeoutException(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _TimeoutException("Processing timed out")


@contextmanager
def _alarm_timeout(seconds: int) -> Iterator[None]:
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


class CodeMetricsAnalyzer:
    """Reusable code-metric helpers shared by adoption and maintenance scripts."""

    CODE_EXTENSIONS = {
        ".cs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cc",
        ".cxx",
        ".hxx",
        ".erl",
        ".hrl",
        ".f",
        ".f90",
        ".for",
        ".f95",
        ".gd",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".kt",
        ".kts",
        ".lua",
        ".m",
        ".mm",
        ".pl",
        ".pm",
        ".t",
        ".php",
        ".sql",
        ".pks",
        ".pkb",
        ".py",
        ".pyw",
        ".r",
        ".rb",
        ".rs",
        ".scala",
        ".sol",
        ".st",
        ".iec",
        ".swift",
        ".ttcn",
        ".ttcn3",
        ".ts",
        ".tsx",
        ".vue",
        ".zig",
        ".sh",
        ".bash",
        ".zsh",
        ".dart",
    }

    KEYWORD_COMPLEXITY_PATTERNS = [
        r"\bif\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bswitch\b",
        r"\bcase\b",
        r"\bcatch\b",
        r"&&",
        r"\|\|",
        r"\?",
    ]

    @classmethod
    def is_programmatic_code(cls, filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in cls.CODE_EXTENSIONS

    @staticmethod
    def clean_patch(patch_text: str) -> str:
        if not patch_text:
            return ""
        lines = patch_text.splitlines()
        return "\n".join(line[1:] for line in lines if line.startswith("+") and not line.startswith("+++"))

    @classmethod
    def estimate_cc_by_keywords(cls, content: str) -> int:
        if not content:
            return 0
        return sum(len(re.findall(pattern, content)) for pattern in cls.KEYWORD_COMPLEXITY_PATTERNS)

    @classmethod
    def calculate_metrics(cls, code: str, filename: str, timeout_seconds: int = 5) -> tuple[int, float]:
        if not code or not cls.is_programmatic_code(filename):
            return 0, 0.0

        if len(code) > 100000 or any(len(line) > 1000 for line in code.splitlines()):
            return len(code.splitlines()), 1.0

        try:
            with _alarm_timeout(timeout_seconds):
                analysis = lizard.analyze_file.analyze_source_code(filename, code)
            loc = analysis.nloc
            complexity = analysis.average_cyclomatic_complexity or 0.0
            if loc > 0 and complexity == 0:
                complexity = 1.0
            return loc, float(complexity)
        except _TimeoutException:
            return len(code.splitlines()), 1.0
        except Exception:
            return len(code.splitlines()), 1.0

    @classmethod
    def patch_metrics(cls, patch_text: str, filename: str) -> tuple[int, float]:
        return cls.calculate_metrics(cls.clean_patch(patch_text), filename)

    @classmethod
    def patch_metrics_with_radon(cls, patch_text: str, filename: str) -> tuple[int, int]:
        code_content = cls.clean_patch(patch_text)
        if not code_content:
            return 0, 0

        try:
            sloc = analyze(code_content).sloc
        except Exception:
            sloc = len(code_content.splitlines())

        try:
            ext = os.path.splitext(filename)[1].lower()
            if ext == ".py":
                complexity = sum(block.complexity for block in cc_visit(code_content))
            else:
                complexity = cls.estimate_cc_by_keywords(code_content)
        except Exception:
            complexity = 0

        return sloc, complexity

