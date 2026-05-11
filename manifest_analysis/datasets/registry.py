"""Canonical dataset locations for each manifest family."""

from __future__ import annotations

from dataclasses import dataclass

from manifest_analysis.utils.paths import (
    DERIVED_ADOPTION_DIR,
    DERIVED_COMMITS_DIR,
    DERIVED_MISC_DIR,
    DERIVED_READABILITY_DIR,
    DERIVED_SECTIONS_DIR,
    DERIVED_STATIC_DIR,
    ORIGINAL_DATASETS_DIR,
)


@dataclass(frozen=True)
class ManifestDataset:
    key: str
    raw_dump_filename: str

    @property
    def original_path(self):
        return ORIGINAL_DATASETS_DIR / f"{self.key}_dataset.csv"

    @property
    def static_path(self):
        return DERIVED_STATIC_DIR / f"{self.key}_static_dataset.csv"

    @property
    def sections_path(self):
        return DERIVED_SECTIONS_DIR / f"{self.key}_sections.csv"

    @property
    def commit_changes_path(self):
        return DERIVED_COMMITS_DIR / f"{self.key}_commit_changes.csv"

    @property
    def adoption_commits_path(self):
        return DERIVED_ADOPTION_DIR / f"{self.key}_adoption_commits.csv"

    @property
    def tool_only_adoption_path(self):
        return DERIVED_ADOPTION_DIR / f"{self.key}_only_adoption_dataset.csv"

    @property
    def flesch_score_path(self):
        return DERIVED_READABILITY_DIR / f"{self.key}_flesch_score.csv"

    @property
    def flesch_score_strip_path(self):
        return DERIVED_READABILITY_DIR / f"{self.key}_flesch_score_strip.csv"

    @property
    def filtered_dataset_path(self):
        return DERIVED_MISC_DIR / f"filtered_{self.key}_dataset.csv"

    @property
    def filtered_sections_path(self):
        return DERIVED_MISC_DIR / f"filtered_{self.key}_sections.csv"

    @property
    def filtered_commits_path(self):
        return DERIVED_MISC_DIR / f"filtered_{self.key}_commits.csv"

    @property
    def missing_from_sections_path(self):
        return DERIVED_MISC_DIR / f"missing_from_sections_{self.key}.csv"

    @property
    def missing_in_sections_path(self):
        return DERIVED_MISC_DIR / f"missing_in_sections_{self.key}.csv"


MANIFEST_DATASETS = {
    dataset.key: dataset
    for dataset in (
        ManifestDataset("agents", "agents_data_dump.csv"),
        ManifestDataset("claude", "claude_data_dump.csv"),
        ManifestDataset("copilot-instructions", "copilot_data_dump.csv"),
    )
}


def get_manifest_dataset(key: str) -> ManifestDataset:
    return MANIFEST_DATASETS[key]


def iter_manifest_datasets():
    return MANIFEST_DATASETS.values()
