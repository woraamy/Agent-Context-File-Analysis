"""Recompute Flesch scores after aggressively stripping non-alphabetic text."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.flesch_comparison import (
    PY_READABILITY_DISABLED_REASON,
    PY_READABILITY_ENABLED,
    process_dataset,
    save_dataset,
    strip_code_blocks,
)
from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.paths import DERIVED_READABILITY_DIR, ensure_dir


NON_ALPHA_RE = re.compile(r"[^A-Za-z\.\!\?\s]+")
WHITESPACE_RE = re.compile(r"\s+")
BULLET_LINE_RE = re.compile(r"(^|\n)\s*[-*+]\s+", re.MULTILINE)
CAMEL_CASE_BOUNDARY_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")


def split_camel_case(value: str) -> str:
    """Insert spaces into CamelCase tokens so syllable counters see real words."""
    return CAMEL_CASE_BOUNDARY_RE.sub(" ", value)


def normalize_markdown_lists(value: str) -> str:
    """Treat Markdown list newlines as sentence boundaries."""
    def replacer(match: re.Match[str]) -> str:
        prefix = match.group(1)
        return f"{prefix}. "

    return BULLET_LINE_RE.sub(replacer, value)


def clean_text(text: str | None) -> str:
    without_code = strip_code_blocks(text)
    with_sentences = normalize_markdown_lists(without_code)
    spaced_camel = split_camel_case(with_sentences)
    letters_only = NON_ALPHA_RE.sub(" ", spaced_camel).replace("\n", " ")
    compressed = WHITESPACE_RE.sub(" ", letters_only)
    return compressed.strip()


def main() -> None:
    ensure_dir(DERIVED_READABILITY_DIR)
    for dataset in iter_manifest_datasets():
        print(f"\n=== Processing {dataset.key} dataset (stripped) ===")
        comparison_df = process_dataset(dataset, clean_text)
        save_dataset(comparison_df, dataset.flesch_score_strip_path)

    if not PY_READABILITY_ENABLED and PY_READABILITY_DISABLED_REASON:
        print(
            "\nNote: py-readability-metrics scores were skipped after encountering an "
            "unrecoverable NLTK resource error. Install the missing corpora via "
            f"`nltk.download()` if you need those values. ({PY_READABILITY_DISABLED_REASON})"
        )


if __name__ == "__main__":
    main()
