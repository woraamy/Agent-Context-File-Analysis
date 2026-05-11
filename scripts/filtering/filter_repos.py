from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.paths import DERIVED_MISC_DIR, ensure_dir


def filter_repositories_data(input_file, output_file, min_commits):
    """
    Filters the claude_md_repositories_with_updates.csv based on stargazers_count
    and total_repo_commits_after_claude_md_initial criteria.
    """
    print("--- Starting Repository Filtering Process ---")

    # --- 1. Load Data ---
    df_repos = None
    if input_file.exists():
        try:
            df_repos = pd.read_csv(input_file)
            print(f"Loaded '{input_file}' successfully. Initial entries: {len(df_repos)}")
        except Exception as e:
            print(f"Error loading '{input_file}': {e}")
            return
    else:
        print(f"Error: Input file '{input_file}' not found. Please ensure it exists.")
        return

    if df_repos.empty:
        print("Input DataFrame is empty. No data to filter.")
        return

    # --- 2. Filter Data ---
    print(
        f"Filtering repositories with total_repo_commits_after_manifest_initialization > {min_commits}...")
    #
    # # Ensure columns exist and are numeric (handling potential NaNs)
    # if 'stargazers_count' not in df_repos.columns:
    #     print("Warning: 'stargazers_count' column not found. Skipping star filter.")
    #     df_repos['stargazers_count'] = 0  # Create a dummy column to avoid errors
    # else:
    #     df_repos['stargazers_count'] = pd.to_numeric(df_repos['stargazers_count'], errors='coerce').fillna(0)

    if 'total_repo_commits_after_manifest_initialization' not in df_repos.columns:
        print("Warning: 'total_repo_commits_after_manifest_initialization' column not found. Skipping commit filter.")
        df_repos['total_repo_commits_after_manifest_initialization'] = 0  # Create a dummy column to avoid errors
    else:
        df_repos['total_repo_commits_after_manifest_initialization'] = pd.to_numeric(
            df_repos['total_repo_commits_after_manifest_initialization'], errors='coerce').fillna(0)

    # Apply the filter criteria
    filtered_df = df_repos[
        df_repos['total_repo_commits_after_manifest_initialization'] > min_commits
        ].copy()

    print(f"Filtered entries: {len(filtered_df)}")

    # --- 3. Save Filtered Data ---
    if not filtered_df.empty:
        try:
            filtered_df.to_csv(output_file, index=False)
            print(f"Successfully saved filtered data to '{output_file}'.")
            print("\nSample of filtered data:")
            print(filtered_df.head())
        except Exception as e:
            print(f"Error saving filtered data to '{output_file}': {e}")
    else:
        print("No repositories matched the filter criteria. Output file not created.")

    print("\n--- Repository Filtering Process Complete ---")


if __name__ == "__main__":
    ensure_dir(DERIVED_MISC_DIR)
    for dataset in iter_manifest_datasets():
        filter_repositories_data(
            input_file=dataset.original_path,
            output_file=dataset.filtered_dataset_path,
            min_commits=40,
        )
