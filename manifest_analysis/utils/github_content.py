from __future__ import annotations

import base64

from manifest_analysis.utils.github_client import GitHubClient


class GitHubContentService:
    def __init__(self, client: GitHubClient = None):
        self.client = client or GitHubClient()

    def get_repo_default_branch(self, owner: str, repo: str) -> str | None:
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            resp = self.client.get(api_url, timeout=30)
            if resp.status_code != 200:
                return None
            return resp.json().get("default_branch")
        except Exception:
            return None

    def get_file_metadata(self, owner: str, repo: str, file_path: str, ref: str | None = None) -> dict | None:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        params = {"ref": ref} if ref else None
        try:
            resp = self.client.get(api_url, params=params, timeout=30)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    def get_file_content(self, owner: str, repo: str, file_path: str, ref: str | None = None) -> str | None:
        """Fetch file content using the GitHub contents API and return decoded text."""
        data = self.get_file_metadata(owner, repo, file_path, ref=ref)
        if not data:
            return None
        if data.get("encoding") == "base64" and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return None

    def get_file_content_and_sha(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: str | None = None,
    ) -> tuple[str | None, str | None]:
        data = self.get_file_metadata(owner, repo, file_path, ref=ref)
        if not data:
            return None, None

        content = None
        if data.get("encoding") == "base64" and "content" in data:
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return content, data.get("sha")


GitHubFetcher = GitHubContentService
