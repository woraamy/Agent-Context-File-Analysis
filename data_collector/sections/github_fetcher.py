from ..repositories.github_client import GitHubClient
import base64


class GitHubFetcher:
    def __init__(self, client: GitHubClient = None):
        self.client = client or GitHubClient()

    def get_file_content(self, owner: str, repo: str, file_path: str) -> str | None:
        """Fetch file content using the GitHub contents API and return decoded text or None."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        try:
            resp = self.client.get(api_url, timeout=30)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get('encoding') == 'base64' and 'content' in data:
                return base64.b64decode(data['content']).decode('utf-8')
            return None
        except Exception:
            return None
