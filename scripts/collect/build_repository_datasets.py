"""Build the three canonical original manifest datasets and commit datasets."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.collectors.repository_collector import RepoCollector
from manifest_analysis.datasets.registry import iter_manifest_datasets


def process_agentic_manifest_from_csv(output_name, csv_filename):
    collector = RepoCollector()
    collector.process_agentic_manifest_from_csv(output_name, csv_filename)


if __name__ == "__main__":
    for dataset in iter_manifest_datasets():
        try:
            process_agentic_manifest_from_csv(dataset.key, dataset.raw_dump_filename)
        except Exception as e:
            print(f"\n✗ Error processing {dataset.key}: {e}")
            traceback.print_exc()
