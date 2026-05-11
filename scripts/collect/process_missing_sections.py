#!/usr/bin/env python3
"""Reprocess files that are missing from filtered section datasets."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.section_analyzer import SectionAnalyzer
from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.github_content import GitHubContentService


CONTENT_SERVICE = GitHubContentService()
SECTION_ANALYZER = SectionAnalyzer()
SECTION_COLUMNS = SectionAnalyzer.expected_columns()


def reprocess_missing_files(agent_manifests):
    """Add newly analyzable rows to filtered sections and prune failed dataset rows."""
    for manifest_key in agent_manifests:
        dataset = get_manifest_dataset(manifest_key)
        print(f"\n{'=' * 20} Reprocessing: {dataset.key.upper()} {'=' * 20}")

        missing_file_path = dataset.missing_from_sections_path
        dataset_path = dataset.filtered_dataset_path
        sections_path = dataset.filtered_sections_path

        if not missing_file_path.exists():
            print(f"No missing files report found for '{dataset.key}'. Skipping.")
            continue

        try:
            df_missing = pd.read_csv(missing_file_path)
            df_dataset = pd.read_csv(dataset_path)
            df_sections = pd.read_csv(sections_path)
        except FileNotFoundError as e:
            print(f"ERROR: Could not load required file: {e}. Skipping '{dataset.key}'.")
            continue

        if df_missing.empty:
            print(f"Missing files report for '{dataset.key}' is empty. No work to do.")
            continue

        print(f"Found {len(df_missing)} missing files to reprocess for '{dataset.key}'.")
        new_sections = []
        rows_to_remove_indices = []

        for _, row in df_missing.iterrows():
            owner = row["repository_owner"]
            repo = row["repository_name"]
            file_path = row["file_path"]
            print(f"  -> Processing: {owner}/{repo}/{file_path}")

            match = df_dataset[
                (df_dataset["repository_owner"] == owner) &
                (df_dataset["repository_name"] == repo) &
                (df_dataset["file_path"] == file_path)
            ]

            ref = None
            file_url = row.get("file_url", "")
            if not match.empty:
                match_row = match.iloc[0]
                if not file_url:
                    file_url = match_row.get("file_url", "")
                if "branch" in match.columns:
                    ref = match_row.get("branch")

            content = CONTENT_SERVICE.get_file_content(owner, repo, file_path, ref=ref)
            analysis_metrics = SECTION_ANALYZER.analyze(content or "")

            if analysis_metrics:
                new_section_row = {
                    "repository_owner": owner,
                    "repository_name": repo,
                    "file_url": file_url,
                }
                for column in SECTION_COLUMNS[3:]:
                    new_section_row[column] = analysis_metrics.get(column, 0.0)
                new_sections.append(new_section_row)
                print("    SUCCESS: Analyzed and staged for addition.")
            elif not match.empty:
                rows_to_remove_indices.extend(match.index.tolist())
                print("    FAILURE: Could not analyze. Staged for removal from dataset.")

            time.sleep(0.1)

        if new_sections:
            df_new_sections = pd.DataFrame(new_sections)
            df_updated_sections = pd.concat([df_sections, df_new_sections], ignore_index=True)
            for column in SECTION_COLUMNS:
                if column not in df_updated_sections.columns:
                    df_updated_sections[column] = 0.0

            df_updated_sections = df_updated_sections[SECTION_COLUMNS]
            for column in df_updated_sections.columns:
                if "total_h" in column:
                    df_updated_sections[column] = df_updated_sections[column].fillna(0).astype(int)
                elif "median" in column or "avg" in column:
                    df_updated_sections[column] = df_updated_sections[column].fillna(0.0).astype(float)

            df_updated_sections.to_csv(sections_path, index=False)
            print(f"\nAdded {len(new_sections)} new entries to '{sections_path}'.")

        if rows_to_remove_indices:
            df_dataset.drop(index=rows_to_remove_indices, inplace=True)
            df_dataset.to_csv(dataset_path, index=False)
            print(f"Removed {len(rows_to_remove_indices)} un-analyzable files from '{dataset_path}'.")

        if not new_sections and not rows_to_remove_indices:
            print("\nNo changes were made to the datasets.")

        print(f"\n{'=' * 20} Finished Reprocessing: {dataset.key.upper()} {'=' * 20}")


if __name__ == "__main__":
    print("--- Starting Reprocessing of Missing Manifest Files ---")
    reprocess_missing_files(["agents", "copilot-instructions", "claude"])
    print("\n--- All missing files have been reprocessed. ---")
