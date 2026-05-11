import pandas as pd
import requests
import os
import time
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

# --- Configuration ---
# Your GitHub Personal Access Token is required for API requests.
github_token = "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"
if not github_token:
    github_token = input("Please enter your GitHub Personal Access Token: ")

headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {github_token}"
}

# Input file from your previous runs
INPUT_CSV = "../claude_md_repositories_with_updates.csv"

# Final output files
OUTPUT_REPO_DATASET = "claude_dataset.csv"
OUTPUT_COMMIT_CHANGES = "claude_commit_changes.csv"

# Set the threshold date for collecting commit data.
# Using 2025 to match the example data provided.
COMMIT_DATE_THRESHOLD = datetime(2025, 7, 31, 23, 59, 59, tzinfo=timezone.utc)


# --- Helper Functions (from previous scripts, adapted for this task) ---

def handle_rate_limit(response, api_name="API"):
    if "X-RateLimit-Remaining" in response.headers:
        remaining = int(response.headers["X-RateLimit-Remaining"])
        if remaining < 15:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_duration = max(reset_time - time.time() + 5, 0)
            print(f"Approaching {api_name} rate limit. Waiting for {int(wait_duration)} seconds.")
            time.sleep(wait_duration)


def count_sections_changed(patch_content):
    if not isinstance(patch_content, str): return 0
    heading_regex = re.compile(r'^(#+)\s*(.*)$')
    changed_sections = set()
    for line in patch_content.split('\n'):
        if line.startswith('+') or line.startswith('-'):
            stripped_line = line[1:].strip()
            match = heading_regex.match(stripped_line)
            if match:
                changed_sections.add(match.group(2).strip())
    return len(changed_sections)


def assign_commit_range(count):
    if pd.isna(count) or count < 0: return "N/A"
    count = int(count)
    lower = (count // 10) * 10
    upper = lower + 9
    return f"{lower}-{upper}"


def search_manifest_files(filename, size_qualifier=""):
    query = f"filename:{filename}"
    if size_qualifier: query += f" size:{size_qualifier}"
    print(f"Executing search query: '{query}'")
    base_url = "https://api.github.com/search/code"
    params = {"q": query, "per_page": 100, "page": 1}
    results = []
    while True:
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=45)
            response.raise_for_status()
            handle_rate_limit(response, "Search API")
            data = response.json()
            items = data.get("items", [])
            if not items: break
            results.extend(items)
            if len(results) >= 1000 or 'rel="next"' not in response.headers.get("Link", ""):
                if len(results) >= 1000: print("Warning: 1000-result limit hit for this query slice.")
                break
            params['page'] += 1
        except requests.exceptions.RequestException as e:
            print(f"Error during search for query '{query}': {e}")
            break
    print(f"Found {len(results)} instances for query '{query}'.")
    return results


def get_repo_and_file_details(owner, repo, file_url):
    details = {"stargazers_count": None, "forks_count": None, "created_at": None, "pushed_at": None, "updated_at": None,
               "lines_of_claude": None}
    try:
        repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(repo_api_url, headers=headers, timeout=30)
        response.raise_for_status()
        handle_rate_limit(response, f"Repo Details for {owner}/{repo}")
        repo_data = response.json()
        details.update({k: repo_data.get(k) for k in details.keys() if k != 'lines_of_claude'})

        raw_file_url = file_url.replace("/blob/", "/raw/")
        file_response = requests.get(raw_file_url, headers=headers, timeout=30)
        file_response.raise_for_status()
        details["lines_of_claude"] = len(file_response.text.splitlines())
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch details for {owner}/{repo}: {e}")
    return details


def get_commit_details(owner, repo, file_path, threshold_date):
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"path": file_path, "per_page": 100, "page": 1}
    file_commits = []
    while True:
        try:
            response = requests.get(commits_url, headers=headers, params=params, timeout=45)
            response.raise_for_status()
            handle_rate_limit(response, f"Commits List for {owner}/{repo}")
            commits_data = response.json()
            if not commits_data: break

            for commit in commits_data:
                commit_date = pd.to_datetime(commit.get("commit", {}).get("author", {}).get("date")).tz_convert('UTC')
                if commit_date > threshold_date: continue

                commit_sha = commit.get("sha")
                detail_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
                detail_response = requests.get(detail_url, headers=headers, timeout=30)
                handle_rate_limit(detail_response, f"Commit Detail for {commit_sha[:7]}")

                if detail_response.status_code == 200:
                    for file_change in detail_response.json().get("files", []):
                        if file_change.get("filename") == file_path:
                            file_commits.append({
                                "repository_owner": owner, "repository_name": repo, "file_path": file_path,
                                "commit_sha": commit_sha, "commit_message": commit.get("commit", {}).get("message"),
                                "commit_url": commit.get("html_url"), "commit_date": commit_date,
                                "lines_added": file_change.get("additions", 0),
                                "lines_deleted": file_change.get("deletions", 0),
                                "patch_content": file_change.get("patch", "")
                            })
                            break

            if 'rel="next"' in response.headers.get("Link", ""):
                params['page'] += 1
            else:
                break
        except requests.exceptions.RequestException as e:
            print(f"Error fetching commit details for {owner}/{repo}/{file_path}: {e}")
            break

    file_commits_sorted = sorted(file_commits, key=lambda x: x['commit_date'])
    first_commit_date = file_commits_sorted[0]['commit_date'].isoformat() if file_commits_sorted else None
    return file_commits_sorted, first_commit_date


def get_total_repo_commits_after_date(owner, repo, since_date_str):
    if pd.isna(since_date_str): return None
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"since": since_date_str, "per_page": 1}
    try:
        response = requests.head(api_url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        handle_rate_limit(response)
        link_header = response.headers.get("Link")
        if not link_header:
            get_response = requests.get(api_url, headers=headers, params={"since": since_date_str}, timeout=30)
            return len(get_response.json())
        links = requests.utils.parse_header_links(link_header)
        for link in links:
            if link.get("rel") == "last":
                query_params = parse_qs(urlparse(link.get("url")).query)
                return int(query_params.get("page", [0])[0])
        return 0
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not get total commits for {owner}/{repo}: {e}")
        return None


# --- Main Execution ---
if __name__ == "__main__":
    # 1. Load Existing Data
    existing_df = pd.DataFrame()
    if os.path.exists(INPUT_CSV):
        print(f"Reading existing data from '{INPUT_CSV}'...")
        existing_df = pd.read_csv(INPUT_CSV)
    else:
        print(f"Warning: Input file '{INPUT_CSV}' not found. Starting with a fresh search.")

    # 2. Discover All Current Files on GitHub
    print("\nStarting comprehensive GitHub search for 'claude.md' files...")
    all_found_repos_raw = []
    size_ranges = ["<=10000", "10001..50000", "50001..100000", "100001..500000", ">500000"]
    for size in size_ranges:
        all_found_repos_raw.extend(search_manifest_files("claude.md", size_qualifier=size))
        time.sleep(2)

    # 3. Consolidate and Deduplicate the Full List of Repos
    discovered_repos = []
    for item in all_found_repos_raw:
        repo_info = item.get("repository", {})
        discovered_repos.append({
            "repository_owner": repo_info.get("owner", {}).get("login"),
            "repository_name": repo_info.get("name"),
            "file_path": item.get("path")
        })
    discovered_df = pd.DataFrame(discovered_repos)

    # Combine existing and discovered lists
    combined_df = pd.concat([existing_df, discovered_df]).drop_duplicates(
        subset=['repository_owner', 'repository_name', 'file_path']
    ).reset_index(drop=True)

    print(f"\nFound {len(discovered_df)} current instances. Total unique repositories to process: {len(combined_df)}")

    # 4. Process Every Repository
    final_repo_data = []
    all_commit_data = []

    total_repos = len(combined_df)
    for index, row in combined_df.iterrows():
        owner, repo, path = row['repository_owner'], row['repository_name'], row['file_path']
        print(f"\n--- [{index + 1}/{total_repos}] Processing: {owner}/{repo}/{path} ---")

        # Get latest repo/file stats (stars, forks, lines, etc.)
        # Construct file_url manually for robustness
        file_url = f"https://github.com/{owner}/{repo}/blob/HEAD/{path}"
        repo_details = get_repo_and_file_details(owner, repo, file_url)
        if not repo_details['stargazers_count']: continue  # Skip if repo details failed

        # Get all commit history up to the threshold date
        commits, first_commit_date = get_commit_details(owner, repo, path, COMMIT_DATE_THRESHOLD)
        if not commits:
            print("  No commits found for this file before the threshold date. Skipping.")
            continue

        all_commit_data.extend(commits)

        # Get total repo commits after initialization
        total_commits = get_total_repo_commits_after_date(owner, repo, first_commit_date)

        # Assemble the final row for the main dataset
        final_repo_data.append({
            "repository_owner": owner, "repository_name": repo,
            "repository_url": f"https://github.com/{owner}/{repo}",
            "file_path": path, "file_url": file_url,
            "stargazers_count": repo_details['stargazers_count'],
            "forks_count": repo_details['forks_count'],
            "created_at": repo_details['created_at'],
            "pushed_at": repo_details['pushed_at'],
            "updated_at": repo_details['updated_at'],
            "lines_of_claude": repo_details['lines_of_claude'],
            "manifest_specific_commit_count": len(commits),
            "first_manifest_commit_date": first_commit_date,
            "total_repo_commits_after_manifest_initialization": total_commits
        })

    # 5. Create, Format, and Save Final DataFrames
    print("\n--- Finalizing and saving output files ---")
    if final_repo_data:
        # Create main dataset
        df_repo_final = pd.DataFrame(final_repo_data)
        df_repo_final['commit_range'] = df_repo_final['manifest_specific_commit_count'].apply(assign_commit_range)

        # Ensure column order matches the example
        final_repo_columns = [
            'repository_owner', 'repository_name', 'repository_url', 'file_path', 'file_url',
            'stargazers_count', 'forks_count', 'created_at', 'pushed_at', 'updated_at',
            'lines_of_claude', 'manifest_specific_commit_count', 'first_manifest_commit_date',
            'commit_range', 'total_repo_commits_after_manifest_initialization'
        ]
        df_repo_final = df_repo_final[final_repo_columns]
        df_repo_final.to_csv(OUTPUT_REPO_DATASET, index=False)
        print(f"✅ Successfully saved repository data to '{OUTPUT_REPO_DATASET}'")

        # Create commit changes dataset
        df_commits_final = pd.DataFrame(all_commit_data)
        for i, commit in enumerate(df_commits_final.sort_values('commit_date').to_dict('records')):
            df_commits_final.loc[i, 'manifest_specific_commit_count'] = i + 1
        df_commits_final['sections_changed_count'] = df_commits_final['patch_content'].apply(count_sections_changed)
        df_commits_final['commit_range'] = df_commits_final['manifest_specific_commit_count'].apply(assign_commit_range)

        final_commit_columns = [
            'repository_owner', 'repository_name', 'file_path', 'commit_sha', 'commit_message',
            'commit_url', 'commit_date', 'lines_added', 'lines_deleted', 'patch_content',
            'manifest_specific_commit_count', 'sections_changed_count', 'commit_range'
        ]
        df_commits_final = df_commits_final[final_commit_columns]
        df_commits_final.to_csv(OUTPUT_COMMIT_CHANGES, index=False)
        print(f"✅ Successfully saved commit changes data to '{OUTPUT_COMMIT_CHANGES}'")
    else:
        print("No data was processed. Output files were not created.")

    print("\nAll tasks complete. ✨")