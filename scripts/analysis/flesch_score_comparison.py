"""Compare stored Flesch scores against fresh calculations from static content."""

from __future__ import annotations

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


def clean_text(text: str | None) -> str:
    return strip_code_blocks(text).strip()


def main() -> None:
    ensure_dir(DERIVED_READABILITY_DIR)
    for dataset in iter_manifest_datasets():
        print(f"\n=== Processing {dataset.key} dataset ===")
        comparison_df = process_dataset(dataset, clean_text)
        save_dataset(comparison_df, dataset.flesch_score_path)

    if not PY_READABILITY_ENABLED and PY_READABILITY_DISABLED_REASON:
        print(
            "\nNote: py-readability-metrics scores were skipped after encountering an "
            "unrecoverable NLTK resource error. Install the missing corpora via "
            f"`nltk.download()` if you need those values. ({PY_READABILITY_DISABLED_REASON})"
        )


if __name__ == "__main__":
    main()
