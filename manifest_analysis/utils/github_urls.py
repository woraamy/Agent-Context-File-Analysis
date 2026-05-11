"""Helpers for parsing GitHub URLs used across dataset scripts."""

from __future__ import annotations

from urllib.parse import urlparse


def extract_file_path_from_github_url(url: str) -> str:
    """Extract a repository file path from a GitHub blob URL."""
    if not isinstance(url, str):
        return ""

    try:
        parsed_path = urlparse(url).path
        parts = parsed_path.split("/blob/")
        if len(parts) <= 1:
            return ""

        path_after_blob_and_sha = parts[1]
        if "/" not in path_after_blob_and_sha:
            return path_after_blob_and_sha
        return path_after_blob_and_sha.split("/", 1)[1]
    except Exception:
        return ""
