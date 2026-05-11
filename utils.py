"""Backwards-compatible shim for legacy `utils` imports."""

from __future__ import annotations

from manifest_analysis.utils.text import fetch_file_content, truncate_to_tokens


__all__ = ["truncate_to_tokens", "fetch_file_content"]
