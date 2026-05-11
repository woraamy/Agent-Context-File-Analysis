# Replication Package for "Agent READMEs: An Empirical Study of Context Files for Agentic Coding"

[![arXiv](https://img.shields.io/badge/arXiv-2511.12884-b31b1b.svg)](https://arxiv.org/abs/2511.12884)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-AgentREADMEs-yellow?logo=huggingface)](https://huggingface.co/datasets/hao-li/AgentREADMEs)

- Paper: https://arxiv.org/abs/2511.12884
- Dataset: https://huggingface.co/datasets/hao-li/AgentREADMEs

## Repository Structure

```text
agentic_manifests_analysis/
├── manifest_analysis/    # Reusable Python package with shared collectors, analysis, and utils
├── scripts/              # Runnable entry points grouped by workflow
│   ├── collect/          #   GitHub collection and dataset-building flows
│   ├── datasets/         #   Dataset summarization and commit-metric updates
│   ├── maintenance/      #   Backfills, verification, and repair scripts
│   ├── analysis/         #   Readability and exploratory analysis
│   ├── classification/   #   Classification generation and evaluation
│   ├── filtering/        #   Filtering, sampling, and missing-data helpers
│   ├── statistics/       #   Statistical analysis exports
│   └── research/         #   Research-specific one-off helpers
├── datasets/
│   ├── original/         #   Canonical manifest datasets
│   └── derived/          #   Static, sections, commits, adoption, statistics, and more
├── raw_datasets/         # Raw data dumps used as collection inputs
├── archive/              # Legacy or superseded scripts kept for reference
├── tests/                # Regression checks for core helpers
└── .github/              # Repository-level GitHub guidance files
```

## Setup

```bash
pip install -r requirements.txt
```

## Current Working Layout

The repository has been refactored so the active code paths are easier to follow:

```text
agentic_manifests_analysis/
├── README.md
├── manifest_analysis/   # Reusable Python package with shared logic
├── scripts/             # Runnable entry points grouped by workflow
├── datasets/            # Managed datasets split into original/ and derived/
├── raw_datasets/        # Raw CSV dumps used as collection inputs
├── archive/             # Legacy or superseded scripts kept for reference
└── tests/               # Regression checks for collection and metric helpers
```

The older directories referenced above are preserved in this README for historical context, but the main day-to-day workflow now goes through `manifest_analysis/`, `scripts/`, and `datasets/`.

## What Lives Where

### `manifest_analysis/`

This is the shared package used by the refactored scripts.

- `collectors/`: repository and commit collection helpers
- `analysis/`: section analysis, readability comparison, and code-metric utilities
- `datasets/`: canonical dataset path registry
- `utils/`: GitHub clients, path helpers, token handling, and text/readability utilities

### `scripts/`

These are the runnable entry points grouped by purpose:

- `scripts/collect/`: build repository, static-content, section, and adoption datasets
- `scripts/datasets/`: summarize or post-process dataset files
- `scripts/maintenance/`: repair, backfill, and verification utilities
- `scripts/analysis/`: readability and exploratory analysis scripts
- `scripts/classification/`: classification generation and evaluation
- `scripts/filtering/`: sampling, filtering, and missing-data helpers
- `scripts/statistics/`: statistical analysis exports
- `scripts/research/`: research-specific helpers

### `datasets/`

Managed datasets are now split by role:

- `datasets/original/`: the three canonical manifest datasets
- `datasets/derived/static/`: original datasets enriched with static content
- `datasets/derived/sections/`: markdown structure metrics
- `datasets/derived/commits/`: commit-history datasets
- `datasets/derived/adoption/`: adoption-focused commit datasets
- `datasets/derived/classification/`: classification inputs and outputs
- `datasets/derived/readability/`: Flesch-score and readability exports
- `datasets/derived/statistics/`: summary tables and significance-test outputs
- `datasets/derived/manual_inspection/`, `research/`, `backups/`, `misc/`: supporting artifacts

## Common Workflows

If you want to rebuild or refresh the main datasets locally, the most common entry points are:

```bash
python3 scripts/collect/build_repository_datasets.py
python3 scripts/collect/static_files_collection.py
python3 scripts/collect/build_section_datasets.py
python3 scripts/datasets/update_commit_metrics.py
python3 scripts/maintenance/update_datasets_with_static.py
```

Useful follow-up scripts include:

```bash
python3 scripts/datasets/summarize_datasets.py
python3 scripts/analysis/flesch_score_comparison.py
python3 scripts/classification/measure_accuracy.py
```

## Environment Notes

Some scripts expect credentials or optional local resources:

- `GITHUB_TOKEN`: used for GitHub API access and higher rate limits
- `OPENAI_API_KEY`: used by classification scripts that call OpenAI models
- `nltk_data_cache/`: local cache for readability-related NLTK resources

Generated/local directories such as `myenv/`, `venv/`, `__pycache__/`, and `.pytest_cache/` are not part of the research artifact itself.

## Verification

The refactored codebase has lightweight verification coverage in `tests/`, and the package/scripts tree is designed so modules can also be sanity-checked with:

```bash
python3 -m compileall manifest_analysis scripts tests
```

## Citation

```bibtex
@article{agentreadmes2025,
  title={Agent READMEs: An Empirical Study of Context Files for Agentic Coding},
  author={Worawalan Chatlatanagulchai and Hao Li and Yutaro Kashiwa and Brittany Reid and Kundjanasith Thonglek and Pattara Leelaprute and Arnon Rungsawang and Bundit Manaskasemsak and Bram Adams and Ahmed E. Hassan and Hajimu Iida},
  year={2025},
  url={https://arxiv.org/abs/2511.12884}
}
```
