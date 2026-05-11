# Scripts

The `scripts/` folder contains runnable entry points grouped by workflow rather than by historical origin.

## Layout

### `scripts/collect`

Collection and refresh workflows.

- `build_repository_datasets.py`: builds `datasets/original/*.csv` and `datasets/derived/commits/*.csv`
- `static_files_collection.py`: creates `datasets/derived/static/*.csv`
- `build_section_datasets.py`: creates `datasets/derived/sections/*.csv`
- `analyze_adoption.py`: derives adoption commit datasets
- `retry_failed_files.py`: retries static-content fetch failures with branch detection

### `scripts/datasets`

Dataset-level transformations and summaries.

- `update_commit_metrics.py`: adds added/deleted readability metrics to commit datasets
- `summarize_datasets.py`: emits a compact dataset summary CSV
- `sum_dataset.py`: lightweight summary helper

### `scripts/filtering`

Filtering, matching, and manual-sampling utilities.

- `filter_repos.py`
- `filter_commits.py`
- `choose_samples.py`
- `pick_random_files.py`
- `match_labels.py`

### `scripts/maintenance`

Repair, recalculation, and backfill scripts.

- `update_datasets_with_static.py`
- `recalculate_metrics_from_static.py`
- `recalculate_codex_complexity.py`
- `verify_commit_metrics.py`

### `scripts/analysis`

Exploratory analysis scripts, especially readability and adoption summaries.

### `scripts/statistics`

Inferential and descriptive statistics scripts plus export helpers.

### `scripts/classification`

Classification model, evaluation, and per-sample comparison scripts.

### `scripts/research`

Research-specific helpers such as manual-label disagreement counting.

## Recommended Order

For a full refresh from raw inputs:

1. `python3 scripts/collect/build_repository_datasets.py`
2. `python3 scripts/collect/static_files_collection.py`
3. `python3 scripts/collect/build_section_datasets.py`
4. `python3 scripts/datasets/update_commit_metrics.py`
5. `python3 scripts/maintenance/update_datasets_with_static.py`

## Legacy Scripts

Superseded or backup scripts were moved to [archive/legacy_scripts](/Users/amyworawalan/Desktop/agentic_manifests_analysis/archive/legacy_scripts).
