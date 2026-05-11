#!/usr/bin/env python3
"""Recompute complexity scores using stripped-text Flesch Reading Ease.

This script mirrors the sanitization flow used in
`analytics/flesch_strip_comparison.py`, but focuses on updating the
`complexity_score` column inside each `*_dataset.csv` file
(`agents`, `claude`, `copilot-instructions`). It reads the corresponding
static dataset to access full manifest text, strips non-alphabetic
characters, computes Textstat's Flesch Reading Ease, and overwrites the
dataset CSV in place with the new scores.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import textstat
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets


CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
NON_ALPHA_RE = re.compile(r"[^A-Za-z\.\!\?\s]+")
WHITESPACE_RE = re.compile(r"\s+")
BULLET_LINE_RE = re.compile(r"(^|\n)\s*[-*+]\s+", re.MULTILINE)
CAMEL_CASE_BOUNDARY_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")


@dataclass(frozen=True)
class DatasetConfig:
	"""Pair paths for a dataset and its static content."""

	name: str
	dataset_path: Path
	static_path: Path


def strip_code_blocks(text: str) -> str:
	return CODE_BLOCK_RE.sub(" ", text)


def split_camel_case(value: str) -> str:
	return CAMEL_CASE_BOUNDARY_RE.sub(" ", value)


def normalize_markdown_lists(value: str) -> str:
	def replacer(match: re.Match[str]) -> str:
		prefix = match.group(1)
		return f"{prefix}. "

	return BULLET_LINE_RE.sub(replacer, value)


def clean_text(text: Optional[str]) -> str:
	if not text or not isinstance(text, str):
		return ""

	without_code = strip_code_blocks(text)
	with_sentences = normalize_markdown_lists(without_code)
	spaced_camel = split_camel_case(with_sentences)
	letters_only = NON_ALPHA_RE.sub(" ", spaced_camel).replace("\n", " ")
	compressed = WHITESPACE_RE.sub(" ", letters_only)
	return compressed.strip()


def compute_textstat_score(text: str) -> Optional[float]:
	if len(text) < 10:
		return None
	try:
		score = textstat.flesch_reading_ease(text)
	except Exception:
		return None
	if score is None or math.isnan(score):
		return None
	return float(score)


def create_fallback_key(
	owner: Optional[str],
	repo: Optional[str],
	file_url: Optional[str],
) -> Optional[str]:
	if not (owner and repo and file_url):
		return None
	return f"{owner}||{repo}||{file_url}"


def build_static_lookup(static_df: pd.DataFrame) -> Dict[str, str]:
	lookup: Dict[str, str] = {}
	for _, row in static_df.iterrows():
		text = row.get("static_content", "") or ""
		key = row.get("file_composite_key")
		fallback = create_fallback_key(
			row.get("repository_owner"),
			row.get("repository_name"),
			row.get("file_url"),
		)

		if key:
			lookup[key] = text
		if fallback and fallback not in lookup:
			lookup[fallback] = text
	return lookup


def recompute_dataset(config: DatasetConfig) -> None:
	print(f"\n=== Updating {config.name} dataset ===")
	if not config.dataset_path.exists():
		raise FileNotFoundError(f"Missing dataset file: {config.dataset_path}")
	if not config.static_path.exists():
		raise FileNotFoundError(f"Missing static dataset file: {config.static_path}")

	dataset_df = pd.read_csv(config.dataset_path)
	static_df = pd.read_csv(config.static_path)
	static_lookup = build_static_lookup(static_df)

	new_scores = []
	empty_count = 0

	for _, row in dataset_df.iterrows():
		key = row.get("file_composite_key")
		if not key:
			key = create_fallback_key(
				row.get("repository_owner"),
				row.get("repository_name"),
				row.get("file_url"),
			)

		raw_text = static_lookup.get(key or "", "")
		cleaned = clean_text(raw_text)
		score = compute_textstat_score(cleaned)
		if score is None:
			empty_count += 1
			new_scores.append(pd.NA)
		else:
			new_scores.append(score)

	dataset_df["complexity_score"] = new_scores
	dataset_df.to_csv(config.dataset_path, index=False)

	total = len(dataset_df)
	print(
		f"  ↳ Wrote {config.dataset_path.name} (rows={total}, missing_scores={empty_count})"
	)


def main() -> None:
	configs = [
		DatasetConfig(dataset.key, dataset.original_path, dataset.static_path)
		for dataset in iter_manifest_datasets()
	]

	for config in configs:
		recompute_dataset(config)

	print("\nDone. All dataset CSVs now contain stripped-text Flesch scores.")


if __name__ == "__main__":
	main()
