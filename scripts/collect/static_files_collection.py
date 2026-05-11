"""Collect static GitHub file content for each original dataset row."""

from __future__ import annotations

import csv
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.github_content import GitHubContentService


CONTENT_SERVICE = GitHubContentService()


def get_file_content_and_commit(owner, repo, file_path, branch):
    """Retrieve file content and the GitHub blob SHA for a repository file."""
    try:
        return CONTENT_SERVICE.get_file_content_and_sha(owner, repo, file_path, ref=branch)
    except Exception as exc:
        print(f"  ⚠️  Unexpected error for {owner}/{repo}/{file_path}: {exc}")
        return None, None


def process_dataset(input_csv, output_csv, dataset_name):
    """
    Process a dataset CSV file and create a new one with static content.
    
    Args:
        input_csv: Path to input CSV file
        output_csv: Path to output CSV file
        dataset_name: Name of the dataset (for logging)
    """
    print(f"Processing {dataset_name}")

    if not input_csv.exists():
        print(f"Input file not found: {input_csv}")
        return
    
    # Read the input CSV
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"Total rows to process: {len(rows)}")
    
    # Add new columns
    new_fieldnames = list(fieldnames) + ['static_content', 'file_commit']
    
    # Process each row
    processed_rows = []
    success_count = 0
    failed_count = 0
    
    for idx, row in enumerate(rows, 1):
        owner = row['repository_owner']
        repo = row['repository_name']
        file_path = row['file_path']
        branch = row['branch']
        
        print(f"\n[{idx}/{len(rows)}] Processing: {owner}/{repo}/{file_path}")
        
        # Get file content and commit
        content, commit_sha = get_file_content_and_commit(owner, repo, file_path, branch)
        
        if content is not None and commit_sha is not None:
            row['static_content'] = content
            row['file_commit'] = commit_sha
            success_count += 1
            print(f"  ✓ Success! Content length: {len(content)} chars, Commit: {commit_sha[:8]}")
        else:
            row['static_content'] = ''
            row['file_commit'] = ''
            failed_count += 1
            print(f"  ✗ Failed to retrieve content")
        
        processed_rows.append(row)
        
        # Progress update every 10 rows
        if idx % 10 == 0:
            print(f"\n📈 Progress: {idx}/{len(rows)} ({success_count} success, {failed_count} failed)")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Write the output CSV
    print(f"\nWriting output to: {output_csv}")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)
    
    print(f"\n{dataset_name} complete!")
    print(f"   Success: {success_count}/{len(rows)}")
    print(f"   Failed: {failed_count}/{len(rows)}")
    print(f"   Output: {output_csv}")


def main():
    """Main execution function."""
    print("="*80)
    print("GitHub Static File Content Collector")
    print("="*80)
    
    for dataset in iter_manifest_datasets():
        process_dataset(dataset.original_path, dataset.static_path, f"{dataset.key} dataset")
    
    print("All datasets processed!")


if __name__ == "__main__":
    main()
