"""Central path definitions for the repository."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASETS_ROOT = PROJECT_ROOT / "datasets"
ORIGINAL_DATASETS_DIR = DATASETS_ROOT / "original"
DERIVED_DATASETS_DIR = DATASETS_ROOT / "derived"
RAW_DATASETS_DIR = PROJECT_ROOT / "raw_datasets"
FIGURES_DIR = PROJECT_ROOT / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

DERIVED_ADOPTION_DIR = DERIVED_DATASETS_DIR / "adoption"
DERIVED_BACKUPS_DIR = DERIVED_DATASETS_DIR / "backups"
DERIVED_CLASSIFICATION_DIR = DERIVED_DATASETS_DIR / "classification"
DERIVED_COMMITS_DIR = DERIVED_DATASETS_DIR / "commits"
DERIVED_MANUAL_INSPECTION_DIR = DERIVED_DATASETS_DIR / "manual_inspection"
DERIVED_MISC_DIR = DERIVED_DATASETS_DIR / "misc"
DERIVED_READABILITY_DIR = DERIVED_DATASETS_DIR / "readability"
DERIVED_RESEARCH_DIR = DERIVED_DATASETS_DIR / "research"
DERIVED_SECTIONS_DIR = DERIVED_DATASETS_DIR / "sections"
DERIVED_STATIC_DIR = DERIVED_DATASETS_DIR / "static"
DERIVED_STATISTICS_DIR = DERIVED_DATASETS_DIR / "statistics"


def ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path

