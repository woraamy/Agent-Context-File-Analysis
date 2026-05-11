from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.code_metrics import CodeMetricsAnalyzer
from manifest_analysis.utils.paths import DERIVED_COMMITS_DIR, ensure_dir


def infer_filename_from_row(row: pd.Series) -> str:
    """Infer a filename-like value so shared metric helpers can detect extensions."""
    for column in ["file_path", "file", "filename", "path"]:
        value = row.get(column)
        if pd.notna(value) and value:
            return str(value)
    return ""


def process_individual_datasets(datasets_dir: Path = DERIVED_COMMITS_DIR) -> None:
    """Process each canonical commit dataset and save first-commit complexity files."""
    ensure_dir(datasets_dir)
    files = sorted(datasets_dir.glob("*_commit_changes.csv"))

    for dataset_path in files:
        print(f"Processing: {dataset_path.name}...")
        try:
            df = pd.read_csv(dataset_path, dtype=str)
        except Exception as e:
            print(f"Error reading {dataset_path}: {e}")
            continue

        if "manifest_specific_commit_count" not in df.columns:
            print(f"Skipping {dataset_path.name}: missing 'manifest_specific_commit_count'.")
            continue

        try:
            counts = pd.to_numeric(df["manifest_specific_commit_count"], errors="coerce")
            subset = df[counts == 1].copy()
        except Exception:
            subset = df[df["manifest_specific_commit_count"] == "1"].copy()

        if subset.empty:
            print(f"No first-manifest commits found in {dataset_path.name}.")
            continue

        results = []
        for _, row in subset.iterrows():
            patch = row.get("patch_content")
            if pd.isna(patch) or not patch:
                continue

            filename = infer_filename_from_row(row)
            sloc, complexity = CodeMetricsAnalyzer.patch_metrics_with_radon(str(patch), filename)
            results.append(
                {
                    "repository_owner": row.get("repository_owner", ""),
                    "repository_name": row.get("repository_name", ""),
                    "file_path": row.get("file_path", ""),
                    "commit_sha": row.get("commit_sha", ""),
                    "sloc_in_patch": sloc,
                    "complexity_in_patch": complexity,
                }
            )

        output_path = datasets_dir / dataset_path.name.replace(
            "_commit_changes.csv",
            "_first_commit_complexity.csv",
        )
        output_df = pd.DataFrame(results)
        if output_df.empty:
            print(f"No patch rows with analyzable content found in {dataset_path.name}.")
            continue

        output_df.to_csv(output_path, index=False)
        print(f"Successfully saved {len(output_df)} rows to {output_path}")


if __name__ == "__main__":
    process_individual_datasets()
