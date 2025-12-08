import os
import time
import pandas as pd

from .github_fetcher import GitHubFetcher
from .analyzer import SectionAnalyzer


class SectionsRunner:
    def __init__(self, fetcher: GitHubFetcher = None, analyzer: SectionAnalyzer = None):
        self.fetcher = fetcher or GitHubFetcher()
        self.analyzer = analyzer or SectionAnalyzer()

    def process_and_save_manifest_sections(self, input_csv_path: str, output_csv_path: str):
        print(f"\n--- Starting Analysis for '{input_csv_path}' ---")

        if not os.path.exists(input_csv_path):
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

            markdown_content = self.fetcher.get_file_content(owner, repo, file_path)

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

        all_possible_cols = ['repository_owner', 'repository_name', 'file_url']
        for i in range(1, 7): all_possible_cols.append(f'total_h{i}')
        for p in range(1, 6):
            for c in range(p + 1, 7): all_possible_cols.append(f"median_h{c}_under_h{p}")
        for i in range(1, 7): all_possible_cols.extend([f'avg_loc_h{i}', f'median_loc_h{i}'])

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
    dataset_prefixes = ['agents', 'claude', 'copilot-instructions']
    for prefix in dataset_prefixes:
        input_file = f"../datasets/{prefix}_dataset.csv"
        output_file = f"../datasets/{prefix}_sections.csv"
        runner.process_and_save_manifest_sections(input_file, output_file)


if __name__ == '__main__':
    main()
