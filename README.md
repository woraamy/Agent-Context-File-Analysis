# Agentic Manifests Analysis

This repository analyzes agent instruction manifests such as `AGENTS.md`, `CLAUDE.md`, and `copilot-instructions.md`, then derives commit, readability, adoption, classification, and statistics datasets from them.

The project is organized around three clear areas:

- `manifest_analysis/`: reusable Python package code
- `scripts/`: runnable scripts grouped by workflow
- `datasets/`: data split into `original/` and `derived/`

Legacy one-off or superseded scripts were moved to `archive/legacy_scripts/` so the active workflow is easier to follow.

## Top-Level Layout

```text
agentic_manifests_analysis/
├── README.md
├── manifest_analysis/
│   ├── analysis/
│   ├── classification/
│   ├── collectors/
│   ├── datasets/
│   └── utils/
├── scripts/
│   ├── analysis/
│   ├── classification/
│   ├── collect/
│   ├── datasets/
│   ├── filtering/
│   ├── maintenance/
│   ├── research/
│   └── statistics/
├── datasets/
│   ├── original/
│   └── derived/
├── docs/
├── archive/
├── raw_datasets/
└── tests/
```

Local/generated folders such as `myenv/`, `venv/`, `nltk_data_cache/`, `__pycache__/`, `.pytest_cache/`, and `.DS_Store` are intentionally omitted from the structure above.

## Package Guide

### `manifest_analysis/collectors`

- `repository_collector.py`: builds the three canonical original datasets and commit datasets from `raw_datasets/`
- `commit_collector.py`: fetches per-file commit history from GitHub

### `manifest_analysis/analysis`

- `section_analyzer.py`: shared markdown structure analysis for `*_sections.csv`
- `code_metrics.py`: shared code-metric helpers used by adoption and maintenance scripts
- `flesch_comparison.py`: shared readability comparison pipeline used by the Flesch audit scripts

### `manifest_analysis/utils`

- `paths.py`: canonical repository and dataset paths
- `github_client.py`: thin GitHub API client
- `github_content.py`: higher-level file content fetch helpers
- `github_urls.py`: GitHub blob URL parsing helpers used by filtering workflows
- `readability.py`: shared patch/readability logic
- `repository.py`: raw dump path parsing and repository-level helpers
- `text.py`: token truncation and generic file-content loading helpers
- `token_manager.py`: token rotation support for GitHub-heavy workflows

### `manifest_analysis/datasets`

- `registry.py`: central mapping for `agents`, `claude`, and `copilot-instructions`

## Script Guide

See [scripts/README.md](/Users/amyworawalan/Desktop/agentic_manifests_analysis/scripts/README.md) for the detailed script map.

Common entry points:

- `python3 scripts/collect/build_repository_datasets.py`
- `python3 scripts/collect/static_files_collection.py`
- `python3 scripts/collect/build_section_datasets.py`
- `python3 scripts/datasets/update_commit_metrics.py`
- `python3 scripts/maintenance/update_datasets_with_static.py`

## Dataset Guide

See [datasets/README.md](/Users/amyworawalan/Desktop/agentic_manifests_analysis/datasets/README.md) for the complete dataset layout.

In short:

- `datasets/original/`: the three canonical manifest datasets
- `datasets/derived/`: all computed outputs, grouped by purpose
- `raw_datasets/`: raw CSV dumps used as collection inputs

## Import Path Changes

The main import cleanup is:

- Old: `from utils import truncate_to_tokens`
  New: `from manifest_analysis.utils.text import truncate_to_tokens`
- Old: `from token_manager import token_manager`
  New: `from manifest_analysis.utils.token_manager import token_manager`
- Old: `from data_collector.repositories.repo_collector import RepoCollector`
  New: `from manifest_analysis.collectors.repository_collector import RepoCollector`
- Old: ad hoc path strings like `../datasets/claude_dataset.csv`
  New: `get_manifest_dataset("claude").original_path`

## Environment

The refactor removed hardcoded GitHub tokens from active scripts.

Use environment variables instead:

- `GITHUB_TOKEN` for GitHub API access
- `OPENAI_API_KEY` for classification scripts
- `GPT_MODEL` optionally overrides the default OpenAI model in `scripts/classification/train_gpt.py`

## Notes

- `raw_datasets/` remains top-level by design.
- The original three manifest datasets now live only in `datasets/original/`.
- Derived datasets are intentionally split by purpose so analysis outputs do not sit next to source datasets.
