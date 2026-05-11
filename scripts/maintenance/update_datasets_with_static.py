"""Sync original and section datasets from the canonical static datasets."""

from __future__ import annotations

import csv
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.section_analyzer import SectionAnalyzer
from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.readability import ReadabilityMetrics


SECTION_ANALYZER = SectionAnalyzer()


def create_file_key(owner, repo, file_url):
    """Create a unique key for matching files across datasets."""
    return ReadabilityMetrics.create_file_key(owner, repo, file_url)


def update_original_dataset(original_csv, static_csv, output_csv, dataset_name):
    """
    Update original dataset to only include entries in static dataset
    and update branch names if they changed.
    
    Args:
        original_csv: Path to original dataset (e.g., claude_dataset.csv)
        static_csv: Path to static dataset (e.g., claude_static_dataset.csv)
        output_csv: Path to save updated original dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Updating Original Dataset: {dataset_name}")
    print(f"{'='*80}")
    
    # Read static dataset to get the valid entries
    static_entries = {}
    with open(static_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = create_file_key(row['repository_owner'], row['repository_name'], row['file_url'])
            static_entries[key] = row
    
    print(f"📊 Static dataset has {len(static_entries)} entries")
    
    # Read original dataset
    with open(original_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_fieldnames = reader.fieldnames
        original_rows = list(reader)
    
    print(f"📊 Original dataset has {len(original_rows)} entries")
    
    # Filter and update original rows
    updated_rows = []
    matched = 0
    updated_branches = 0
    
    for row in original_rows:
        key = create_file_key(row['repository_owner'], row['repository_name'], row['file_url'])
        
        if key in static_entries:
            matched += 1
            static_row = static_entries[key]
            
            # Check if branch name changed
            if row['branch'] != static_row['branch']:
                print(f"  📝 Updating branch for {row['repository_owner']}/{row['repository_name']}: "
                      f"{row['branch']} → {static_row['branch']}")
                row['branch'] = static_row['branch']
                updated_branches += 1
            
            updated_rows.append(row)
    
    # Write updated dataset
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=original_fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    removed = len(original_rows) - matched
    
    print(f"\n✅ Update complete!")
    print(f"   Matched: {matched}/{len(original_rows)}")
    print(f"   Removed: {removed}")
    print(f"   Branch names updated: {updated_branches}")
    print(f"   Output: {output_csv}")


def update_sections_dataset(static_csv, sections_csv, output_csv, dataset_name):
    """
    Recalculate sections using static_content from static dataset.
    
    Args:
        static_csv: Path to static dataset with static_content column
        sections_csv: Path to existing sections dataset (for reference structure)
        output_csv: Path to save updated sections dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Updating Sections Dataset: {dataset_name}")
    print(f"{'='*80}")
    
    sections_fieldnames = SectionAnalyzer.expected_columns()
    
    # Read static dataset
    with open(static_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        static_rows = list(reader)
    
    print(f"📊 Processing {len(static_rows)} files from static dataset")
    
    # Process each file and calculate sections
    sections_rows = []
    success = 0
    failed = 0
    
    for idx, row in enumerate(static_rows, 1):
        owner = row['repository_owner']
        repo = row['repository_name']
        file_url = row['file_url']
        static_content = row.get('static_content', '')
        
        if idx % 100 == 0:
            print(f"  Progress: {idx}/{len(static_rows)} ({success} success, {failed} failed)")
        
        if not static_content:
            print(f"  ⚠️  [{idx}] No content for {owner}/{repo}")
            failed += 1
            continue
        
        try:
            # Analyze the markdown structure
            metrics = SECTION_ANALYZER.analyze(static_content)
            
            if not metrics:
                print(f"  ⚠️  [{idx}] No headers found in {owner}/{repo}")
                failed += 1
                continue
            
            # Create the sections row
            sections_row = {
                'repository_owner': owner,
                'repository_name': repo,
                'file_url': file_url
            }
            
            # Add all metrics
            for field in sections_fieldnames[3:]:  # Skip owner, repo, url
                sections_row[field] = metrics.get(field, 0.0)
            
            sections_rows.append(sections_row)
            success += 1
            
        except Exception as e:
            print(f"  ❌ [{idx}] Error processing {owner}/{repo}: {e}")
            failed += 1
            continue
    
    # Write updated sections dataset
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sections_fieldnames)
        writer.writeheader()
        writer.writerows(sections_rows)
    
    print(f"\n✅ Sections update complete!")
    print(f"   Success: {success}/{len(static_rows)}")
    print(f"   Failed: {failed}/{len(static_rows)}")
    print(f"   Output: {output_csv}")


def main():
    """Main execution function."""
    print("="*80)
    print("Update Datasets with Static Content")
    print("="*80)
    
    for dataset in iter_manifest_datasets():
        # Step 1: Update original dataset
        update_original_dataset(
            str(dataset.original_path),
            str(dataset.static_path),
            str(dataset.original_path),
            f"{dataset.key} original dataset"
        )
        
        # Step 2: Update sections dataset
        update_sections_dataset(
            str(dataset.static_path),
            str(dataset.sections_path),
            str(dataset.sections_path),
            f"{dataset.key} sections dataset"
        )
    
    print("\n" + "="*80)
    print("🎉 All datasets updated successfully!")
    print("="*80)
    print("\nUpdated files:")
    for dataset in iter_manifest_datasets():
        print(f"  ✅ {dataset.original_path}")
        print(f"  ✅ {dataset.sections_path}")


if __name__ == "__main__":
    main()
