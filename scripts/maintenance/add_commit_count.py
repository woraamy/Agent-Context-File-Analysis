from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.github_client import GitHubClient


GITHUB_CLIENT = GitHubClient()
if "Authorization" not in GITHUB_CLIENT.headers:
    print("Warning: GITHUB_TOKEN is not set. GitHub API calls will use lower rate limits.")


def get_total_repo_commits_after_date(owner, repo, since_date_str):
    """Efficiently count total commits in a repository after a specific date."""
    if pd.isna(since_date_str) or not since_date_str:
        return None

    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"since": since_date_str, "per_page": 1}

    try:
        response = GITHUB_CLIENT.head(api_url, params=params, timeout=30)
        response.raise_for_status()

        link_header = response.headers.get("Link")
        if not link_header:
            get_response = GITHUB_CLIENT.get(api_url, params={"since": since_date_str}, timeout=30)
            get_response.raise_for_status()
            return len(get_response.json())

        links = requests.utils.parse_header_links(link_header)
        last_page_url = None
        for link in links:
            if link.get("rel") == "last":
                last_page_url = link.get("url")
                break

        if last_page_url:
            query_params = parse_qs(urlparse(last_page_url).query)
            return int(query_params.get("page", [0])[0])
        return 0
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Warning: Repository {owner}/{repo} not found (404).")
        else:
            print(f"Warning: HTTP Error for {owner}/{repo}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Warning: Request Error for {owner}/{repo}: {e}")
        return None


def add_commit_counts_to_dataset(csv_filepath: Path):
    """Read a dataset CSV, add a total commit count column, and save it."""
    print("\n" + "=" * 50)
    print(f"Processing file: {csv_filepath}")
    print("=" * 50)

    if not csv_filepath.exists():
        print(f"Error: File not found at '{csv_filepath}'. Skipping.")
        return

    try:
        df = pd.read_csv(csv_filepath)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    required_cols = ["repository_owner", "repository_name", "first_manifest_commit_date"]
    if not all(col in df.columns for col in required_cols):
        print(f"Error: CSV is missing one of the required columns: {required_cols}. Skipping.")
        return

    new_column_name = "total_repo_commits_after_manifest_initialization"
    if new_column_name not in df.columns:
        df[new_column_name] = pd.NA

    total_rows = len(df)
    for index, row in df.iterrows():
        if pd.notna(row.get(new_column_name)):
            continue

        owner = row["repository_owner"]
        repo = row["repository_name"]
        since_date = row["first_manifest_commit_date"]

        print(f"[{index + 1}/{total_rows}] Fetching commit count for {owner}/{repo}...")
        commit_count = get_total_repo_commits_after_date(owner, repo, since_date)
        df.at[index, new_column_name] = commit_count

        if (index + 1) % 20 == 0:
            print(f"--- Saving progress to {csv_filepath} ---")
            df.to_csv(csv_filepath, index=False)

    print(f"Processing complete. Saving final results to {csv_filepath}.")
    df.to_csv(csv_filepath, index=False)


if __name__ == "__main__":
    for dataset in iter_manifest_datasets():
        add_commit_counts_to_dataset(dataset.original_path)

    print("\n\nAll files processed.")
