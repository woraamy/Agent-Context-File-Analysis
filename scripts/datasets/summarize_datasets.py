#!/usr/bin/env python3
"""Summarize the canonical original and commit datasets.

For each dataset key (agents, claude, copilot-instructions) the script reports:
 - number of rows (files) in {key}_dataset(.csv)
 - number of unique repositories referenced in that dataset
 - number of commit rows in {key}_commit_changes(.csv)
 - number of unique repositories present in the commit changes file
 - number of unique commit SHAs

It writes a small summary CSV to `datasets/derived/statistics/dataset_summary.csv`
and prints a table.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.paths import DERIVED_STATISTICS_DIR, ensure_dir


def count_unique_repos(df: pd.DataFrame) -> int:
    # Prefer explicit owner+name columns
    if {"repository_owner", "repository_name"}.issubset(df.columns):
        return df[["repository_owner", "repository_name"]].drop_duplicates().shape[0]
    # fallback: repository_url
    if "repository_url" in df.columns:
        return df["repository_url"].dropna().astype(str).nunique()
    # fallback: try to parse owner/repo from file_url
    if "file_url" in df.columns:
        owners = set()
        for u in df["file_url"].dropna().astype(str):
            try:
                # Expect URLs like https://github.com/owner/repo/blob/...
                parts = u.split("github.com/")[-1].split("/")
                owner = parts[0]
                repo = parts[1]
                owners.add((owner, repo))
            except Exception:
                continue
        return len(owners)
    # final fallback: count distinct combinations of any repository-like columns
    repo_cols = [c for c in df.columns if "repo" in c.lower() or "repository" in c.lower()]
    if repo_cols:
        return df[repo_cols].drop_duplicates().shape[0]
    return 0


def summarize_dataset(dataset) -> dict:
    dataset_file = dataset.original_path
    commit_file = dataset.commit_changes_path

    summary = {
        "dataset": dataset.key,
        "dataset_file": str(dataset_file) if dataset_file.exists() else None,
        "commit_file": str(commit_file) if commit_file.exists() else None,
        "num_rows": None,
        "unique_repos_in_dataset": None,
        "num_commit_rows": None,
        "unique_repos_in_commits": None,
        "unique_commit_shas": None,
    }

    if dataset_file.exists():
        try:
            df = pd.read_csv(dataset_file, dtype=str).fillna("")
            summary["num_rows"] = int(df.shape[0])
            summary["unique_repos_in_dataset"] = int(count_unique_repos(df))
        except Exception as e:
            summary["num_rows"] = f"error: {e}"

    if commit_file.exists():
        try:
            dc = pd.read_csv(commit_file, dtype=str).fillna("")
            summary["num_commit_rows"] = int(dc.shape[0])
            # unique repos in commits
            if {"repository_owner", "repository_name"}.issubset(dc.columns):
                summary["unique_repos_in_commits"] = int(dc[["repository_owner", "repository_name"]].drop_duplicates().shape[0])
            elif "repository_url" in dc.columns:
                summary["unique_repos_in_commits"] = int(dc["repository_url"].nunique())
            else:
                summary["unique_repos_in_commits"] = int(count_unique_repos(dc))

            # unique commit SHAs
            if "commit_sha" in dc.columns:
                summary["unique_commit_shas"] = int(dc["commit_sha"].dropna().astype(str).nunique())
            else:
                summary["unique_commit_shas"] = None
        except Exception as e:
            summary["num_commit_rows"] = f"error: {e}"

    return summary


def main(out_csv: Optional[Path] = None):
    summaries = []
    for dataset in iter_manifest_datasets():
        summaries.append(summarize_dataset(dataset))

    df_summary = pd.DataFrame(summaries)

    # Print a friendly table
    print("Dataset summary (files / unique repos / commit rows / unique commit shas):")
    for r in summaries:
        print(f"- {r['dataset']}: files={r['num_rows']} repos={r['unique_repos_in_dataset']} commits={r['num_commit_rows']} unique_commits={r['unique_commit_shas']}")

    # Save CSV
    if out_csv is None:
        ensure_dir(DERIVED_STATISTICS_DIR)
        out_csv = DERIVED_STATISTICS_DIR / "dataset_summary.csv"
    try:
        df_summary.to_csv(out_csv, index=False)
        print(f"\nSaved summary to: {out_csv}")
    except Exception as e:
        print(f"Could not save summary CSV: {e}")


if __name__ == "__main__":
    main()
