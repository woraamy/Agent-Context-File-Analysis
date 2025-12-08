"""Utility helpers used by classification code.

This file provides two small helpers used across the classification modules:
- `truncate_to_tokens(text, max_tokens, encoding_name)` — attempts to truncate
  text to a maximum number of tokens using `tiktoken` when available and
  falls back to a naive whitespace-based truncation.
- `fetch_file_content(path_or_url)` — fetches content from a local file path
  or HTTP(S) URL using `requests`.

The implementations are intentionally lightweight and robust to missing
optional dependencies so they work in CI and on developer machines.
"""

from typing import Optional

__all__ = ["truncate_to_tokens", "fetch_file_content"]


def truncate_to_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
	"""Return `text` truncated to at most `max_tokens` tokens.

	If the `tiktoken` package is available it will be used for accurate token
	counts. Otherwise the function falls back to a conservative whitespace
	based truncation so callers still get a shorter string when necessary.
	"""
	if not text or max_tokens <= 0:
		return ""

	try:
		import tiktoken

		enc = tiktoken.get_encoding(encoding_name)
		token_ids = enc.encode(text)
		if len(token_ids) <= max_tokens:
			return text
		truncated = enc.decode(token_ids[:max_tokens])
		return truncated
	except Exception:
		# Fallback: approximate tokens using whitespace splitting. We choose a
		# conservative multiplier (2 words ~= 1 token) to avoid returning too
		# long strings when tiktoken isn't available.
		words = text.split()
		approx_words = max_tokens * 2
		if len(words) <= approx_words:
			return text
		return " ".join(words[:approx_words])


def fetch_file_content(path_or_url: str, timeout: Optional[float] = 10.0) -> str:
	"""Fetch file content from a local path or an HTTP(S) URL.

	- If `path_or_url` starts with 'http://' or 'https://' it will be fetched
	  via `requests` and the response text returned.
	- Otherwise the string is treated as a local filesystem path and opened
	  in text mode using UTF-8.

	The function raises exceptions from `requests` or file IO to let callers
	decide how to handle network/filesystem errors.
	"""
	if not path_or_url:
		return ""

	lowered = path_or_url.lower()
	if lowered.startswith("http://") or lowered.startswith("https://"):
		try:
			import requests

			resp = requests.get(path_or_url, timeout=timeout)
			resp.raise_for_status()
			return resp.text
		except Exception:
			# Re-raise to make failures explicit to the caller
			raise

	# Treat as local file
	with open(path_or_url, "r", encoding="utf-8") as fh:
		return fh.read()

