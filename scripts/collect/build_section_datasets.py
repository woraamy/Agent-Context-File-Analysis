from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.section_analyzer import SectionAnalyzer
from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.github_content import GitHubContentService


class SectionsRunner:
    def __init__(self, fetcher: GitHubContentService = None, analyzer: SectionAnalyzer = None):
        self.fetcher = fetcher or GitHubContentService()
        self.analyzer = analyzer or SectionAnalyzer()

    def process_and_save_manifest_sections(self, input_csv_path: Path, output_csv_path: Path):
        print(f"\n--- Starting Analysis for '{input_csv_path}' ---")

        if not input_csv_path.exists():
            print(f"Error: Input file not found at '{input_csv_path}'. Skipping.")
            return

        try:
            df_input = pd.read_csv(input_csv_path)
        except Exception as e:
            print(f"Error reading '{input_csv_path}': {e}. Skipping.")
            return

        all_results = []
        total_files = len(df_input)

        for index, row in df_input.iterrows():
            owner = row['repository_owner']
            repo = row['repository_name']
            file_path = row['file_path']
            file_url = row.get('file_url', '')

            print(f"[{index + 1}/{total_files}] Processing: {owner}/{repo}/{file_path}")

            markdown_content = self.fetcher.get_file_content(owner, repo, file_path, ref=row.get("branch"))

            if markdown_content:
                analysis_metrics = self.analyzer.analyze(markdown_content)
                file_result = {
                    'repository_owner': owner,
                    'repository_name': repo,
                    'file_url': file_url,
                    **analysis_metrics
                }
                all_results.append(file_result)

            time.sleep(0.1)

        if not all_results:
            print("No manifest files were successfully analyzed. Output file will not be created.")
            return

        df_output = pd.DataFrame(all_results)

        all_possible_cols = SectionAnalyzer.expected_columns()

        for col in all_possible_cols:
            if col not in df_output.columns:
                df_output[col] = 0.0
        df_output = df_output[all_possible_cols]

        try:
            df_output.to_csv(output_csv_path, index=False)
            print(f"\n✅ Success! Analysis complete. Results saved to '{output_csv_path}'")
        except Exception as e:
            print(f"\n❌ Error saving results to '{output_csv_path}': {e}")


def main():
    runner = SectionsRunner()
    for dataset in iter_manifest_datasets():
        runner.process_and_save_manifest_sections(dataset.original_path, dataset.sections_path)


if __name__ == '__main__':
    main()
