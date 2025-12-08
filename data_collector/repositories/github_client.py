import os
import time
import requests


class GitHubClient:
    def __init__(self, token_env_var="GITHUB_TOKEN"):
        github_token = os.getenv(token_env_var)
        if not github_token:
            github_token = input("Please enter your GitHub Personal Access Token (press Enter for unauthenticated access): ")

        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
            print("GitHub token found. Using authenticated requests for higher rate limits.")
        else:
            print("Warning: No GitHub token provided. Using unauthenticated requests, which have lower rate limits.")

    def get(self, url, **kwargs):
        resp = requests.get(url, headers=self.headers, **kwargs)
        self._handle_rate_limit(resp)
        return resp

    def _handle_rate_limit(self, response, api_name="API"):
        if not response or not hasattr(response, 'headers'):
            return
        if "X-RateLimit-Remaining" in response.headers:
            try:
                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                if remaining < 15:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_duration = max(reset_time - time.time() + 5, 0)
                    print(f"Approaching {api_name} rate limit (remaining: {remaining}). Waiting for {int(wait_duration)} seconds.")
                    time.sleep(wait_duration)
            except Exception:
                pass
