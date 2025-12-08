"""
Lightweight orchestrator that exposes the original `process_agentic_manifest_from_csv`
function by delegating to the refactored `RepoCollector` and `CommitCollector` classes.
"""

from .repo_collector import RepoCollector


def process_agentic_manifest_from_csv(output_name, csv_filename):
    collector = RepoCollector()
    collector.process_agentic_manifest_from_csv(output_name, csv_filename)


if __name__ == "__main__":
    manifest_jobs = [
        {"output_name": "agents", "csv_filename": "agents_data_dump.csv"},
        {"output_name": "claude", "csv_filename": "claude_data_dump.csv"},
        {"output_name": "copilot-instructions", "csv_filename": "copilot_data_dump.csv"}
    ]

    for job in manifest_jobs:
        try:
            process_agentic_manifest_from_csv(job['output_name'], job['csv_filename'])
        except Exception as e:
            print(f"\n✗ Error processing {job['output_name']}: {e}")
            import traceback
            traceback.print_exc()