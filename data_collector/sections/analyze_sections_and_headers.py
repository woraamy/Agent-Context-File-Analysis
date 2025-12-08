"""Compatibility wrapper for the sections refactor.

This module keeps the original public function name
`process_and_save_manifest_sections(input_csv_path, output_csv_path)` and
delegates to the new `SectionsRunner` implementation in
`data_collector.sections.runner`.
"""

from .runner import SectionsRunner


def process_and_save_manifest_sections(input_csv_path, output_csv_path):
    runner = SectionsRunner()
    runner.process_and_save_manifest_sections(input_csv_path, output_csv_path)


if __name__ == '__main__':
    runner = SectionsRunner()
    prefixes = ['agents', 'claude', 'copilot-instructions']
    for prefix in prefixes:
        in_file = f"../datasets/{prefix}_dataset.csv"
        out_file = f"../datasets/{prefix}_sections.csv"
        runner.process_and_save_manifest_sections(in_file, out_file)