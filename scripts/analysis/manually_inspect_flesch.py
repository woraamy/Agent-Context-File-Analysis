"""Manually inspect Flesch scores for a random sample of agent manifests.

This script selects 10 random entries across the agent-context datasets,
computes readability scores with textstat, py-readability, and a manual
implementation of the Flesch Reading Ease formula, and saves the results to
`datasets/derived/readability/manual_flesch_inspection.csv` (including the sanitized text used for
inspection).
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import nltk
import pandas as pd
import textstat
from readability import Readability
from readability.exceptions import ReadabilityException
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.paths import DERIVED_READABILITY_DIR, DERIVED_STATIC_DIR


random.seed(42)

DATASETS_ROOT = PROJECT_ROOT / "datasets"
OUTPUT_PATH = DERIVED_READABILITY_DIR / "manual_flesch_inspection.csv"
SAMPLE_SIZE = 10

STATIC_DATASETS = [(dataset.key, dataset.static_path) for dataset in iter_manifest_datasets()]

CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+|\n+")
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass
class SampleEntry:
	"""Represents a sampled manifest entry and its computed scores."""

	dataset: str
	repository_owner: str
	repository_name: str
	repository_url: str
	file_path: str
	text: str
	textstat_score: Optional[float]
	py_readability_score: Optional[float]
	manual_score: Optional[float]


def strip_code_blocks(text: str) -> str:
	return CODE_BLOCK_RE.sub(" ", text)


def prepare_text(text: str) -> str:
	"""Prepare text for readability calculations."""

	cleaned = strip_code_blocks(text)
	return cleaned.strip()


def manual_sentence_count(text: str) -> int:
	sentences = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(text) if segment.strip()]
	return max(1, len(sentences))


def manual_word_list(text: str) -> List[str]:
	return WORD_RE.findall(text)


def count_syllables(word: str) -> int:
	word = word.lower()
	word = re.sub(r"[^a-z]", "", word)
	if not word:
		return 0
	vowels = "aeiouy"
	syllables = 0
	prev_char_is_vowel = False
	for char in word:
		is_vowel = char in vowels
		if is_vowel and not prev_char_is_vowel:
			syllables += 1
		prev_char_is_vowel = is_vowel
	if word.endswith("e") and syllables > 1:
		syllables -= 1
	return max(1, syllables)


def manual_flesch_score(text: str) -> Optional[float]:
	words = manual_word_list(text)
	if not words:
		return None
	sentences = manual_sentence_count(text)
	syllables = sum(count_syllables(word) for word in words)
	word_count = max(1, len(words))
	words_per_sentence = word_count / sentences
	syllables_per_word = syllables / word_count if word_count else 0
	return 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word


def compute_textstat_score(text: str) -> Optional[float]:
	if len(text) < 10:
		return None
	try:
		value = textstat.flesch_reading_ease(text)
		return float(value)
	except Exception:
		return None


def compute_py_score(text: str) -> Optional[float]:
	if len(text) < 10:
		return None
	try:
		result = Readability(text).flesch()
		return float(result.score)
	except (ReadabilityException, ValueError, TypeError, LookupError):
		return None


def load_samples() -> pd.DataFrame:
	rows = []
	for dataset_name, path in STATIC_DATASETS:
		df = pd.read_csv(path)
		df = df[df["static_content"].notna() & (df["static_content"].str.strip() != "")]
		df = df.copy()
		df["dataset"] = dataset_name
		rows.append(df)
	return pd.concat(rows, ignore_index=True)


def select_random_entries(df: pd.DataFrame) -> pd.DataFrame:
	if len(df) <= SAMPLE_SIZE:
		return df
	return df.sample(SAMPLE_SIZE, random_state=42)


def main() -> None:
	try:
		nltk.data.find("tokenizers/punkt")
	except LookupError:
		nltk.download("punkt", quiet=True)

	data = load_samples()
	selection = select_random_entries(data)
	results: List[SampleEntry] = []

	for _, row in selection.iterrows():
		text = prepare_text(row["static_content"])
		textstat_score = compute_textstat_score(text)
		py_score = compute_py_score(text)
		manual_score_value = manual_flesch_score(text)

		results.append(
			SampleEntry(
				dataset=row["dataset"],
				repository_owner=row.get("repository_owner", ""),
				repository_name=row.get("repository_name", ""),
				repository_url=row.get("repository_url", ""),
				file_path=row.get("file_path", row.get("filename", "")),
				text=text,
				textstat_score=textstat_score,
				py_readability_score=py_score,
				manual_score=manual_score_value,
			)
		)

	output_df = pd.DataFrame(
		{
			"dataset": [entry.dataset for entry in results],
			"repository_owner": [entry.repository_owner for entry in results],
			"repository_name": [entry.repository_name for entry in results],
			"repository_url": [entry.repository_url for entry in results],
			"file_path": [entry.file_path for entry in results],
			"textstat_score": [entry.textstat_score for entry in results],
			"py_readability_score": [entry.py_readability_score for entry in results],
			"manual_flesch_score": [entry.manual_score for entry in results],
			"inspection_text": [entry.text for entry in results],
		}
	)

	output_df.to_csv(OUTPUT_PATH, index=False)
	print(f"Saved manual inspection dataset to {OUTPUT_PATH.relative_to(DATASETS_ROOT.parent)}")
	print(output_df[["repository_owner", "repository_name", "textstat_score", "py_readability_score", "manual_flesch_score"]])


if __name__ == "__main__":
	main()
