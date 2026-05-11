"""Text and lightweight I/O helpers used across the project.

This file provides two small helpers used across the classification modules:
- `truncate_to_tokens(text, max_tokens, encoding_name)` — attempts to truncate
  text to a maximum number of tokens using `tiktoken` when available and
  falls back to a naive whitespace-based truncation.
- `fetch_file_content(path_or_url)` — fetches content from a local file path
  or HTTP(S) URL using `requests`.

The implementations are intentionally lightweight and robust to missing
optional dependencies so they work in CI and on developer machines.
"""

from __future__ import annotations

from typing import Optional

__all__ = ["truncate_to_tokens", "fetch_file_content"]


def truncate_to_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    """Return `text` truncated to at most `max_tokens` tokens."""
    if not text or max_tokens <= 0:
        return ""

    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        token_ids = enc.encode(text)
        if len(token_ids) <= max_tokens:
            return text
        return enc.decode(token_ids[:max_tokens])
    except Exception:
        words = text.split()
        approx_words = max_tokens * 2
        if len(words) <= approx_words:
            return text
        return " ".join(words[:approx_words])


def fetch_file_content(path_or_url: str, timeout: Optional[float] = 10.0) -> str:
    """Fetch file content from a local path or an HTTP(S) URL."""
    if not path_or_url:
        return ""

    lowered = path_or_url.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        import requests

        resp = requests.get(path_or_url, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    with open(path_or_url, "r", encoding="utf-8") as fh:
        return fh.read()
