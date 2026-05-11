from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.github_urls import extract_file_path_from_github_url
from manifest_analysis.utils.paths import DERIVED_MISC_DIR, ensure_dir


def process_and_clean_manifest_data(
    agent_manifests,
    delete_extra_entries=False,
    save_missing_reports=False,
):
    """
    Process section data for a list of manifest families using canonical paths.
    """
    ensure_dir(DERIVED_MISC_DIR)

    for manifest_key in agent_manifests:
        dataset = get_manifest_dataset(manifest_key)
        print(f"\n{'=' * 20} Processing: {dataset.key.upper()} {'=' * 20}")

        sections_input_file = dataset.sections_path
        filtered_repos_input_file = dataset.filtered_dataset_path
        filtered_sections_output_file = dataset.filtered_sections_path

        if not sections_input_file.exists():
            print(f"SKIPPING: Raw sections file not found at `{sections_input_file}`")
            continue
        try:
            df_sections_raw = pd.read_csv(sections_input_file)
            print(f"Loaded raw sections from `{sections_input_file}`. Initial entries: {len(df_sections_raw)}")
        except Exception as e:
            print(f"ERROR: Could not load `{sections_input_file}`: {e}")
            continue

        if not filtered_repos_input_file.exists():
            print(f"SKIPPING: Filtered repositories file not found at `{filtered_repos_input_file}`")
            continue
        try:
            df_filtered_repos = pd.read_csv(filtered_repos_input_file)
            print(f"Loaded filtered repositories from `{filtered_repos_input_file}`. Repositories: {len(df_filtered_repos)}")
        except Exception as e:
            print(f"ERROR: Could not load `{filtered_repos_input_file}`: {e}")
            continue

        if df_sections_raw.empty or df_filtered_repos.empty:
            print("WARNING: One or both input DataFrames are empty. Skipping filtering.")
            continue

        df_filtered_repos["repo_identifier"] = (
            df_filtered_repos["repository_owner"] + "/" + df_filtered_repos["repository_name"]
        )
        allowed_repo_identifiers = set(df_filtered_repos["repo_identifier"])
        df_sections_raw["repo_identifier"] = (
            df_sections_raw["repository_owner"] + "/" + df_sections_raw["repository_name"]
        )

        df_sections_filtered = df_sections_raw[
            df_sections_raw["repo_identifier"].isin(allowed_repo_identifiers)
        ].copy()
        df_sections_filtered.drop(columns=["repo_identifier"], inplace=True, errors="ignore")

        print(
            f"Filtered sections entries: {len(df_sections_filtered)} "
            f"(removed {len(df_sections_raw) - len(df_sections_filtered)})"
        )

        try:
            df_sections_filtered.to_csv(filtered_sections_output_file, index=False)
            print(f"Saved filtered sections to `{filtered_sections_output_file}`")
        except Exception as e:
            print(f"ERROR: Could not save filtered sections to `{filtered_sections_output_file}`: {e}")
            continue

        df_filtered_repos["file_composite_key"] = (
            df_filtered_repos["repository_owner"].astype(str) + "||" +
            df_filtered_repos["repository_name"].astype(str) + "||" +
            df_filtered_repos["file_path"].astype(str)
        )

        df_sections_filtered["extracted_file_path"] = df_sections_filtered["file_url"].apply(
            extract_file_path_from_github_url
        )
        df_sections_filtered["file_composite_key"] = (
            df_sections_filtered["repository_owner"].astype(str) + "||" +
            df_sections_filtered["repository_name"].astype(str) + "||" +
            df_sections_filtered["extracted_file_path"].astype(str)
        )

        keys_in_filtered_repos = set(df_filtered_repos["file_composite_key"])
        keys_in_sections = set(df_sections_filtered["file_composite_key"])

        print(f"Unique file entries in filtered sections: {len(keys_in_sections)}")
        print(f"Unique file entries in repository list: {len(keys_in_filtered_repos)}")

        extra_keys = keys_in_sections - keys_in_filtered_repos
        missing_keys = keys_in_filtered_repos - keys_in_sections

        if extra_keys:
            print(
                f"\nWARNING: Found {len(extra_keys)} extra file entries in "
                f"`{filtered_sections_output_file}` not in the repository list."
            )
            if delete_extra_entries:
                original_count = len(df_sections_filtered)
                df_sections_cleaned = df_sections_filtered[
                    ~df_sections_filtered["file_composite_key"].isin(extra_keys)
                ].copy()
                df_sections_cleaned.drop(
                    columns=["extracted_file_path", "file_composite_key"],
                    inplace=True,
                    errors="ignore",
                )
                try:
                    df_sections_cleaned.to_csv(filtered_sections_output_file, index=False)
                    print(f"Removed {original_count - len(df_sections_cleaned)} entries. New total: {len(df_sections_cleaned)}")
                except Exception as e:
                    print(f"ERROR: Could not save cleaned data to `{filtered_sections_output_file}`: {e}")
            else:
                print("Action: No changes made. Re-run with `delete_extra_entries=True` to remove them.")
        else:
            print("\nSUCCESS: No extra file-level entries in sections.")

        if missing_keys:
            print(
                f"\nWARNING: Found {len(missing_keys)} file entries present in repositories "
                f"but missing from sections for `{dataset.key}`."
            )
            df_missing_in_sections = df_filtered_repos[
                df_filtered_repos["file_composite_key"].isin(missing_keys)
            ].copy()
            report_cols = ["repository_owner", "repository_name", "file_path"]
            df_missing_report = df_missing_in_sections[report_cols].drop_duplicates().reset_index(drop=True)
            print(f"Sample missing entries (up to 5):\n{df_missing_report.head()}")

            if save_missing_reports:
                missing_out_file = dataset.missing_in_sections_path
                try:
                    df_missing_report.to_csv(missing_out_file, index=False)
                    print(f"Saved missing-in-sections report to `{missing_out_file}`")
                except Exception as e:
                    print(f"ERROR: Could not save missing report to `{missing_out_file}`: {e}")
        else:
            print("\nSUCCESS: No repository files are missing from sections.")

        repos_in_sections = set(
            df_sections_filtered["repository_owner"] + "/" + df_sections_filtered["repository_name"]
        )
        repos_in_filtered_list = set(
            df_filtered_repos["repository_owner"] + "/" + df_filtered_repos["repository_name"]
        )
        repos_only_in_sections = repos_in_sections - repos_in_filtered_list

        if repos_only_in_sections:
            print(f"WARNING: Found {len(repos_only_in_sections)} repositories in sections not in the main list.")
            for repo_id in sorted(repos_only_in_sections):
                print(f"- {repo_id}")
        else:
            print("SUCCESS: Repository-level consistency confirmed.")

        print(f"\n{'=' * 20} Finished: {dataset.key.upper()} {'=' * 20}")


if __name__ == "__main__":
    process_and_clean_manifest_data(
        agent_manifests=["agents", "copilot-instructions", "claude"],
        delete_extra_entries=False,
        save_missing_reports=False,
    )
