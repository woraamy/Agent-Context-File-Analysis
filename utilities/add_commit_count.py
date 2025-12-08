import pandas as pd
import requests
import os
import time
from urllib.parse import urlparse, parse_qs

# --- Configuration ---
# The script will try to get your GitHub token from an environment variable.
# If it can't find it, it will ask you to enter it manually.
github_token = os.getenv("GITHUB_TOKEN")
if not github_token:
    github_token = input("Please enter your GitHub Personal Access Token: ")

headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {github_token}"
}


# --- Helper Functions ---

def handle_rate_limit(response):
    """Checks the API rate limit and waits if it's running low."""
    if "X-RateLimit-Remaining" in response.headers:
        remaining = int(response.headers["X-RateLimit-Remaining"])
        if remaining < 10:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_duration = max(reset_time - time.time() + 5, 0)
            print(f"Approaching rate limit. Waiting for {int(wait_duration)} seconds.")
            time.sleep(wait_duration)


def get_total_repo_commits_after_date(owner, repo, since_date_str):
    """
    Efficiently counts the total number of commits in a repository after a specific date.
    Returns the count, or None if an error occurs.
    """
    if pd.isna(since_date_str):
        return None

    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"since": since_date_str, "per_page": 1}

    try:
        # Use a HEAD request to get the 'Link' header without downloading commit data
        response = requests.head(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        handle_rate_limit(response)

        link_header = response.headers.get("Link")
        if not link_header:
            # If no Link header, it means there's only one page of results (or zero).
            # We must make a GET request to count the items on this single page.
            get_response = requests.get(api_url, headers=headers, params={"since": since_date_str}, timeout=30)
            get_response.raise_for_status()
            return len(get_response.json())

        # Parse the 'Link' header to find the URL for the last page
        links = requests.utils.parse_header_links(link_header)
        last_page_url = None
        for link in links:
            if link.get("rel") == "last":
                last_page_url = link.get("url")
                break

        if last_page_url:
            # The 'page' number in the last page URL is the total number of commits
            query_params = parse_qs(urlparse(last_page_url).query)
            total_commits = int(query_params.get("page", [0])[0])
            return total_commits
        else:
            return 0  # Should be covered by the "if not link_header" case, but as a fallback.

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Warning: Repository {owner}/{repo} not found (404).")
        else:
            print(f"Warning: HTTP Error for {owner}/{repo}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Warning: Request Error for {owner}/{repo}: {e}")
        return None


# --- Main Processing Function ---

def add_commit_counts_to_dataset(csv_filepath):
    """
    Reads a dataset CSV, adds a column with total commit counts, and saves it.
    """
    print("\n" + "=" * 50)
    print(f"Processing file: {csv_filepath}")
    print("=" * 50)

    if not os.path.exists(csv_filepath):
        print(f"Error: File not found at '{csv_filepath}'. Skipping.")
        return

    try:
        df = pd.read_csv(csv_filepath)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Check for required columns
    required_cols = ['repository_owner', 'repository_name', 'first_manifest_commit_date']
    if not all(col in df.columns for col in required_cols):
        print(f"Error: CSV is missing one of the required columns: {required_cols}. Skipping.")
        return

    new_column_name = 'total_repo_commits_after_manifest_initialization'
    if new_column_name not in df.columns:
        df[new_column_name] = pd.NA

    total_rows = len(df)
    for index, row in df.iterrows():
        # Skip if data is already present
        if pd.notna(row.get(new_column_name)):
            continue

        owner = row['repository_owner']
        repo = row['repository_name']
        since_date = row['first_manifest_commit_date']

        print(f"[{index + 1}/{total_rows}] Fetching commit count for {owner}/{repo}...")

        commit_count = get_total_repo_commits_after_date(owner, repo, since_date)

        df.at[index, new_column_name] = commit_count

        # Save progress every 20 rows
        if (index + 1) % 20 == 0:
            print(f"--- Saving progress to {csv_filepath} ---")
            df.to_csv(csv_filepath, index=False)

    # Final save
    print(f"✅ Processing complete. Saving final results to {csv_filepath}.")
    df.to_csv(csv_filepath, index=False)


# --- Execution Block ---

if __name__ == "__main__":
    # List of the dataset files you want to process
    files_to_process = [
        "agents_dataset.csv",
        "copilot-instructions_dataset.csv",
        "gemini_dataset.csv"
    ]

    for filename in files_to_process:
        add_commit_counts_to_dataset(filename)

    print("\n\nAll files processed. ✨")