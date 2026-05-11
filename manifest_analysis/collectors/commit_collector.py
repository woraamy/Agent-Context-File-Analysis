import time
from typing import Tuple, List


class CommitCollector:
    def __init__(self, github_client):
        self.client = github_client

    def get_commit_details(self, owner: str, repo: str, file_path: str) -> Tuple[List[dict], str]:
        """Gets detailed commit history for a specific file (all commits, no date filter)."""
        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {"path": file_path, "per_page": 100, "page": 1}
        file_commits = []

        while True:
            try:
                response = self.client.get(commits_url, params=params, timeout=30)
                response.raise_for_status()
                commits_data = response.json()

                if not commits_data:
                    break

                for commit in commits_data:
                    commit_date_str = commit.get("commit", {}).get("author", {}).get("date")

                    commit_sha = commit.get("sha")
                    detail_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
                    detail_response = self.client.get(detail_url, timeout=30)

                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        for file_change in detail_data.get("files", []):
                            if file_change.get("filename") == file_path:
                                file_commits.append({
                                    "repository_owner": owner,
                                    "repository_name": repo,
                                    "file_path": file_path,
                                    "commit_sha": commit_sha,
                                    "commit_message": commit.get("commit", {}).get("message"),
                                    "commit_url": commit.get("html_url"),
                                    "commit_date": commit_date_str,
                                    "lines_added": file_change.get("additions", 0),
                                    "lines_deleted": file_change.get("deletions", 0),
                                    "patch_content": file_change.get("patch", "")
                                })
                                break

                if 'rel="next"' in response.headers.get("Link", ""):
                    params['page'] += 1
                else:
                    break
            except Exception as e:
                print(f"Error fetching commit details for {owner}/{repo}/{file_path}: {e}")
                break

        file_commits_sorted = sorted(file_commits, key=lambda x: x['commit_date'])
        for i, commit in enumerate(file_commits_sorted):
            commit['manifest_specific_commit_count'] = i + 1

        first_commit_date = file_commits_sorted[0]['commit_date'] if file_commits_sorted else None
        return file_commits_sorted, first_commit_date
