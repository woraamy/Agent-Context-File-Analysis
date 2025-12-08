"""Backwards-compatible shim for `utils` imports.

Many parts of the repository historically did `from utils import ...`.
After a refactor the canonical implementation lives at
`classification.src.utils`. This module re-exports the key helpers so
old imports continue to work while callers migrate to the canonical path.

The shim tries a few import locations (in priority order) and falls back to
small, explicit error-raising stubs if none are available.
"""
from typing import Optional

try:
    # Preferred canonical location created during refactor
    from classification.src.utils import truncate_to_tokens, fetch_file_content  # type: ignore
except Exception:
    try:
        # Older possible location
        from classification.utils import truncate_to_tokens, fetch_file_content  # type: ignore
    except Exception:
        # Minimal stubs to produce clear errors if nothing is available.
        def truncate_to_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
            raise ImportError(
                "Unable to import `truncate_to_tokens` from `classification.src.utils` or `classification.utils`."
            )

        def fetch_file_content(path_or_url: str, timeout: Optional[float] = 10.0) -> str:
            raise ImportError(
                "Unable to import `fetch_file_content` from `classification.src.utils` or `classification.utils`."
            )

__all__ = ["truncate_to_tokens", "fetch_file_content"]
