# Datasets

The dataset tree is now split into source datasets and derived outputs.

## Layout

```text
datasets/
├── original/
│   ├── agents_dataset.csv
│   ├── claude_dataset.csv
│   └── copilot-instructions_dataset.csv
└── derived/
    ├── adoption/
    ├── backups/
    ├── classification/
    ├── commits/
    ├── manual_inspection/
    ├── misc/
    ├── readability/
    ├── research/
    ├── sections/
    ├── static/
    └── statistics/
```

## Folder Descriptions

### `original/`

The three canonical manifest datasets produced from `raw_datasets/`.

### `derived/static/`

Original datasets enriched with `static_content` and file commit metadata.

### `derived/sections/`

Markdown structure metrics such as heading counts, nesting medians, and LOC-per-section.

### `derived/commits/`

Per-file commit history datasets plus patch-level readability metrics.

### `derived/adoption/`

Adoption-commit datasets and tool-specific adoption subsets.

### `derived/readability/`

Flesch score exports, stripped-text readability exports, and manual readability inspection outputs.

### `derived/classification/`

Ground-truth inputs, prediction inputs, and classification evaluation results.

### `derived/statistics/`

Summary tables, pairwise tests, and label distribution exports.

### `derived/manual_inspection/`

Random samples, same-entry matching files, and annotator-specific datasets.

### `derived/research/`

Research-specific outputs that do not fit the main pipelines cleanly.

### `derived/backups/`

Historical backups retained for reproducibility or manual rollback.

### `derived/misc/`

Filtered datasets, filtered sections, filtered commit subsets, and small helper reports that support manual review or mid-pipeline cleanup.

## Naming Conventions

- Original datasets: `{tool}_dataset.csv`
- Static datasets: `{tool}_static_dataset.csv`
- Section datasets: `{tool}_sections.csv`
- Commit datasets: `{tool}_commit_changes.csv`
- Adoption datasets: `{tool}_adoption_commits.csv`
- Tool-only adoption subsets: `{tool}_only_adoption_dataset.csv`

## Raw Inputs

`raw_datasets/` intentionally remains at the repository root because it represents pre-processing inputs rather than part of the managed dataset output tree.
