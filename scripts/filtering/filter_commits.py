from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.paths import DERIVED_MISC_DIR, ensure_dir


def filter_am_commits(all_commits_file,filtered_repos_file, output_file):
    """
    Filters commit data from 'claude_md_commit_changes_with_sections.csv'
    based on repositories listed in 'filtered_claude_md_repositories.csv'.

    The filtering is done by matching 'repository_owner', 'repository_name',
    and 'file_path' attributes.

    Args:
        all_commits_file (str): Path to the CSV file containing all commit data.
                                Defaults to "claude_md_commit_changes_with_sections.csv".
        filtered_repos_file (str): Path to the CSV file containing the list of
                                   repositories to filter by.
                                   Defaults to "filtered_claude_md_repositories.csv".
        output_file (str): Path where the filtered commit data will be saved.
                           Defaults to "filtered_claude_md_commit_changes_with_sections.csv".
    """
    print(f"Starting filtering process...")

    # --- 1. Load the filtered repositories file ---
    if not filtered_repos_file.exists():
        print(f"Error: The file '{filtered_repos_file}' was not found. Please ensure it's in the same directory as the script or provide the full path.")
        return

    try:
        df_filtered_repos = pd.read_csv(filtered_repos_file)
        print(f"Successfully loaded {len(df_filtered_repos)} filtered repositories from '{filtered_repos_file}'.")
    except Exception as e:
        print(f"Error loading '{filtered_repos_file}': {e}")
        return

    # Extract unique repository combinations (owner, name, file_path) from the filtered repos
    # We convert them to a set of tuples for efficient lookup
    filtered_repo_set = set(
        df_filtered_repos[['repository_owner', 'repository_name', 'file_path']]
        .apply(tuple, axis=1)
    )
    print(f"Identified {len(filtered_repo_set)} unique repositories to filter by.")

    # --- 2. Load the all commits file ---
    if not all_commits_file.exists():
        print(f"Error: The file '{all_commits_file}' was not found. Please ensure it's in the same directory as the script or provide the full path.")
        return

    try:
        df_all_commits = pd.read_csv(all_commits_file)
        print(f"Successfully loaded {len(df_all_commits)} commits from '{all_commits_file}'.")
    except Exception as e:
        print(f"Error loading '{all_commits_file}': {e}")
        return

    # --- 3. Filter Commits ---
    print("Filtering commits...")

    # Create a boolean mask to identify rows that match the filtered repositories
    # We apply the same tuple conversion to each commit row for comparison
    mask = df_all_commits[['repository_owner', 'repository_name', 'file_path']].apply(
        lambda row: tuple(row) in filtered_repo_set, axis=1
    )

    df_filtered_commits = df_all_commits[mask]
    print(f"Found {len(df_filtered_commits)} commits matching the filtered repositories.")

    # --- 4. Write to New CSV ---
    try:
        df_filtered_commits.to_csv(output_file, index=False)
        print(f"Filtered commits saved to '{output_file}'.")
    except Exception as e:
        print(f"Error saving filtered commits to '{output_file}': {e}")


if __name__ == "__main__":
    ensure_dir(DERIVED_MISC_DIR)
    for dataset in iter_manifest_datasets():
        filter_am_commits(
            all_commits_file=dataset.commit_changes_path,
            filtered_repos_file=dataset.filtered_dataset_path,
            output_file=dataset.filtered_commits_path,
        )
