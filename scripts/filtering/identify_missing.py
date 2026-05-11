#!/usr/bin/env python3
"""Identify files present in filtered datasets but missing from filtered sections."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.github_urls import extract_file_path_from_github_url
from manifest_analysis.utils.paths import DERIVED_MISC_DIR, ensure_dir


def identify_missing_files(
    agent_manifests,
    delete_missing=False,
    delete_extra_sections=False,
):
    """Identify filtered dataset rows that never made it into filtered sections."""
    ensure_dir(DERIVED_MISC_DIR)

    for manifest_key in agent_manifests:
        dataset = get_manifest_dataset(manifest_key)
        print(f"\n{'=' * 20} Analyzing: {dataset.key.upper()} {'=' * 20}")

        dataset_file = dataset.filtered_dataset_path
        sections_file = dataset.filtered_sections_path
        output_file = dataset.missing_from_sections_path

        if not dataset_file.exists():
            print(f"ERROR: Dataset file not found: {dataset_file}")
            continue
        if not sections_file.exists():
            print(f"ERROR: Sections file not found: {sections_file}")
            continue

        try:
            df_dataset = pd.read_csv(dataset_file)
            print(f"Loaded dataset from {dataset_file}. Total files: {len(df_dataset)}")
        except Exception as e:
            print(f"ERROR: Could not load {dataset_file}: {e}")
            continue

        try:
            df_sections = pd.read_csv(sections_file)
            print(f"Loaded sections from {sections_file}. Total entries: {len(df_sections)}")
        except Exception as e:
            print(f"ERROR: Could not load {sections_file}: {e}")
            continue

        if df_dataset.empty:
            print("WARNING: Dataset is empty. Skipping.")
            continue

        if df_sections.empty:
            print("WARNING: Sections file is empty. All dataset files are missing.")
            df_missing = df_dataset[["repository_owner", "repository_name", "file_path"]].copy()
            try:
                df_missing.to_csv(output_file, index=False)
                print(f"All {len(df_missing)} files are missing from sections. Saved to: {output_file}")
            except Exception as e:
                print(f"ERROR: Could not save missing files report: {e}")
            continue

        df_dataset["file_composite_key"] = (
            df_dataset["repository_owner"].astype(str) + "||" +
            df_dataset["repository_name"].astype(str) + "||" +
            df_dataset["file_path"].astype(str)
        )

        df_sections["extracted_file_path"] = df_sections["file_url"].apply(
            extract_file_path_from_github_url
        )
        df_sections["file_composite_key"] = (
            df_sections["repository_owner"].astype(str) + "||" +
            df_sections["repository_name"].astype(str) + "||" +
            df_sections["extracted_file_path"].astype(str)
        )

        dataset_keys = set(df_dataset["file_composite_key"])
        sections_keys = set(df_sections["file_composite_key"])
        missing_keys = dataset_keys - sections_keys
        extra_section_keys = sections_keys - dataset_keys

        print(f"Files in dataset: {len(dataset_keys)}")
        print(f"Files in sections: {len(sections_keys)}")
        print(f"Files missing from sections: {len(missing_keys)}")
        print(f"Extra entries in sections file: {len(extra_section_keys)}")

        if extra_section_keys and delete_extra_sections:
            indices_to_remove_sections = df_sections[
                df_sections["file_composite_key"].isin(extra_section_keys)
            ].index
            if not indices_to_remove_sections.empty:
                df_sections.drop(indices_to_remove_sections, inplace=True)
                try:
                    df_sections.to_csv(sections_file, index=False)
                    print(f"SUCCESS: Removed {len(indices_to_remove_sections)} extra entries from '{sections_file}'.")
                except Exception as e:
                    print(f"ERROR: Could not save the updated sections file to '{sections_file}': {e}")

        if missing_keys:
            df_missing = df_dataset[df_dataset["file_composite_key"].isin(missing_keys)].copy()
            report_columns = ["repository_owner", "repository_name", "file_path"]
            if "commit_count" in df_missing.columns:
                report_columns.append("commit_count")
            if "file_url" in df_missing.columns:
                report_columns.append("file_url")

            df_missing_report = df_missing[report_columns].sort_values(
                ["repository_owner", "repository_name", "file_path"]
            ).reset_index(drop=True)

            if delete_missing:
                indices_to_remove = df_dataset[df_dataset["file_composite_key"].isin(missing_keys)].index
                if not indices_to_remove.empty:
                    df_dataset.drop(indices_to_remove, inplace=True)
                    try:
                        df_dataset.to_csv(dataset_file, index=False)
                        print(f"SUCCESS: Removed {len(indices_to_remove)} missing entries from '{dataset_file}'.")
                    except Exception as e:
                        print(f"ERROR: Could not save the updated dataset to '{dataset_file}': {e}")

            try:
                df_missing_report.to_csv(output_file, index=False)
                print(f"Missing files report saved to: {output_file}")
                print(f"\nSummary for {dataset.key}:")
                print(f"- Total repositories with missing files: {df_missing_report['repository_owner'].nunique()}")
                print("- Most common file names:")
                file_names = df_missing_report["file_path"].apply(
                    lambda value: os.path.basename(value) if pd.notna(value) else "unknown"
                )
                top_files = file_names.value_counts().head(5)
                for file_name, count in top_files.items():
                    print(f"  * {file_name}: {count} files")

                print("\nAll missing files:")
                print(
                    df_missing_report[["repository_owner", "repository_name", "file_path"]]
                    .to_string(index=False)
                )
            except Exception as e:
                print(f"ERROR: Could not save missing files report to {output_file}: {e}")
        else:
            print("SUCCESS: All dataset files have corresponding sections entries!")

        print(f"\n{'=' * 20} Finished: {dataset.key.upper()} {'=' * 20}")


def analyze_missing_patterns(agent_manifests):
    """Analyze missing-file patterns across all manifest families."""
    print(f"\n{'=' * 50}")
    print("CROSS-MANIFEST MISSING FILES ANALYSIS")
    print(f"{'=' * 50}")

    all_missing = []
    for manifest_key in agent_manifests:
        dataset = get_manifest_dataset(manifest_key)
        missing_file = dataset.missing_from_sections_path
        if missing_file.exists():
            try:
                df = pd.read_csv(missing_file)
                df["manifest_type"] = dataset.key
                all_missing.append(df)
                print(f"{dataset.key}: {len(df)} missing files")
            except Exception as e:
                print(f"ERROR loading {missing_file}: {e}")

    if not all_missing:
        print("No missing files reports found.")
        return

    df_all_missing = pd.concat(all_missing, ignore_index=True)
    print("\nOverall Statistics:")
    print(f"- Total missing files across all manifests: {len(df_all_missing)}")
    print(
        "- Unique repositories with missing files: "
        f"{df_all_missing.groupby(['repository_owner', 'repository_name']).ngroups}"
    )

    print("\nMost common missing file names across all manifests:")
    file_names = df_all_missing["file_path"].apply(
        lambda value: os.path.basename(value) if pd.notna(value) else "unknown"
    )
    top_files = file_names.value_counts().head(10)
    for file_name, count in top_files.items():
        print(f"  * {file_name}: {count} files")

    print("\nMissing files by manifest type:")
    manifest_counts = df_all_missing["manifest_type"].value_counts()
    for manifest, count in manifest_counts.items():
        print(f"  * {manifest}: {count} files")


if __name__ == "__main__":
    AGENT_MANIFESTS = ["agents", "copilot-instructions", "claude"]
    DELETE_MISSING_FILES = False
    DELETE_EXTRA_SECTIONS = False

    print("Starting missing files identification...")
    identify_missing_files(
        AGENT_MANIFESTS,
        delete_missing=DELETE_MISSING_FILES,
        delete_extra_sections=DELETE_EXTRA_SECTIONS,
    )
    analyze_missing_patterns(AGENT_MANIFESTS)
    print("\nMissing files identification complete!")
