import os
import time
import pandas as pd

from .github_client import GitHubClient
from .utils import parse_file_path, RAW_DATASETS_DIR


class RepoCollector:
    def __init__(self, github_client=None):
        self.client = github_client or GitHubClient()

    def detect_default_branch(self, owner, repo):
        for branch in ['main', 'master']:
            try:
                branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
                response = self.client.get(branch_url, timeout=30)
                if response.status_code == 200:
                    print(f"  ✓ Using branch '{branch}' for {owner}/{repo}")
                    return branch
            except Exception:
                continue

        try:
            repo_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = self.client.get(repo_url, timeout=30)
            if response.status_code == 200:
                repo_data = response.json()
                default_branch = repo_data.get("default_branch", "main")
                print(f"  ✓ Using default branch '{default_branch}' for {owner}/{repo}")
                return default_branch
        except Exception:
            pass

        print(f"  ✗ Could not detect branch for {owner}/{repo}, defaulting to 'main'")
        return 'main'

    def get_repo_and_file_details(self, owner, repo, file_path_in_repo, branch):
        repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
        details = {
            "stargazers_count": None, "forks_count": None, "created_at": None,
            "pushed_at": None, "updated_at": None, "lines_of_code": None
        }

        try:
            response = self.client.get(repo_api_url, timeout=30)
            response.raise_for_status()
            repo_data = response.json()
            details.update({
                "stargazers_count": repo_data.get("stargazers_count"),
                "forks_count": repo_data.get("forks_count"),
                "created_at": repo_data.get("created_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "updated_at": repo_data.get("updated_at"),
            })

            raw_file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path_in_repo}"
            file_response = self.client.get(raw_file_url, timeout=30)
            file_response.raise_for_status()
            details["lines_of_code"] = len(file_response.text.splitlines())

        except Exception as e:
            print(f"  ✗ Could not fetch details for {owner}/{repo}: {e}")

        return details

    def process_agentic_manifest_from_csv(self, output_name, csv_filename, commit_collector=None):
        print("\n" + "=" * 50)
        print(f"Processing job: {output_name} from CSV: {csv_filename}")
        print("=" * 50)

        repo_output_csv = f"../datasets/{output_name}_dataset.csv"
        commit_output_csv = f"../datasets/{output_name}_commit_changes.csv"

        csv_path = os.path.join(RAW_DATASETS_DIR, csv_filename)
        if not os.path.exists(csv_path):
            print(f"✗ Error: CSV file not found: {csv_path}")
            return

        df_input = pd.read_csv(csv_path)
        if 'file_path' not in df_input.columns:
            print(f"✗ Error: 'file_path' column not found in {csv_filename}")
            return

        repo_list = []
        for index, row in df_input.iterrows():
            file_path = row['file_path']
            owner, repo, file_path_in_repo, filename = parse_file_path(file_path)
            if owner and repo and file_path_in_repo:
                repo_list.append({
                    "repository_owner": owner,
                    "repository_name": repo,
                    "file_path": file_path_in_repo,
                    "filename": filename,
                    "original_file_path": file_path
                })
            else:
                print(f"  ✗ Skipping invalid file_path: {file_path}")

        if not repo_list:
            print(f"✗ No valid file paths found in {csv_filename}")
            return

        df_repos = pd.DataFrame(repo_list).drop_duplicates(
            subset=['repository_owner', 'repository_name', 'file_path'],
            keep='first'
        ).reset_index(drop=True)

        print(f"\nTotal unique repositories to process: {len(df_repos)}")

        enriched_data = []
        for index, row in df_repos.iterrows():
            owner = row['repository_owner']
            repo = row['repository_name']
            file_path_in_repo = row['file_path']

            print(f"[{index + 1}/{len(df_repos)}] Processing {owner}/{repo}/{file_path_in_repo}")
            branch = self.detect_default_branch(owner, repo)
            details = self.get_repo_and_file_details(owner, repo, file_path_in_repo, branch)

            file_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{file_path_in_repo}"
            repo_url = f"https://github.com/{owner}/{repo}"

            full_row = {
                **row.to_dict(),
                "repository_url": repo_url,
                "file_url": file_url,
                "branch": branch,
                **details
            }
            enriched_data.append(full_row)
            time.sleep(0.2)

        df_repos_enriched = pd.DataFrame(enriched_data).dropna(subset=['stargazers_count'])
        print(f"\n✓ Successfully enriched {len(df_repos_enriched)} repositories")

        # get commits using provided commit_collector
        all_commit_changes = []
        final_repo_details_list = []

        if commit_collector is None:
            # import here to avoid circular import at module load
            from ..commits.commit_collector import CommitCollector
            commit_collector = CommitCollector(self.client)

        print(f"\nFetching commit history for {len(df_repos_enriched)} repositories...")

        for index, row in df_repos_enriched.iterrows():
            owner = row['repository_owner']
            repo = row['repository_name']
            file_path = row['file_path']

            print(f"[{index + 1}/{len(df_repos_enriched)}] Getting commits for {owner}/{repo}/{file_path}...")
            commits, first_commit_date = commit_collector.get_commit_details(owner, repo, file_path)

            if commits:
                all_commit_changes.extend(commits)
                repo_summary = {
                    **row.to_dict(),
                    "manifest_specific_commit_count": len(commits),
                    "first_manifest_commit_date": first_commit_date
                }
                final_repo_details_list.append(repo_summary)
            else:
                print(f"  ⚠ No commits found for {owner}/{repo}/{file_path}")

            time.sleep(0.2)

        if not final_repo_details_list:
            print(f"\n✗ No repositories with valid commit history found for job '{output_name}'.")
        else:
            print("\n✓ Processing and saving repository dataset...")
            df_repos_final = pd.DataFrame(final_repo_details_list)
            df_repos_final = df_repos_final.rename(columns={"lines_of_code": f"lines_of_{output_name}"})
            os.makedirs("datasets", exist_ok=True)
            df_repos_final.to_csv(repo_output_csv, index=False)
            print(f"Successfully saved repository data to '{repo_output_csv}' ({len(df_repos_final)} repositories)")

        if not all_commit_changes:
            print(f"\n✗ No commit data found for job '{output_name}' before the date threshold.")
        else:
            print("\n✓ Processing and saving commit changes dataset...")
            df_commits = pd.DataFrame(all_commit_changes)
            # lazy import to reuse util
            from .utils import count_sections_changed
            df_commits['sections_changed_count'] = df_commits['patch_content'].apply(count_sections_changed)
            df_commits.to_csv(commit_output_csv, index=False)
            print(f"Successfully saved commit changes data to '{commit_output_csv}' ({len(df_commits)} commits)")
