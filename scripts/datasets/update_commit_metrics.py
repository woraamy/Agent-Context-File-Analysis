"""Add commit-level readability metrics to each derived commit dataset."""

from __future__ import annotations

import csv
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.readability import ReadabilityMetrics


def process_commit_dataset(input_csv, output_csv, dataset_name):
    """
    Process a commit dataset to calculate metrics for deleted and added lines.
    
    Args:
        input_csv: Path to input commit dataset
        output_csv: Path to output dataset with new metrics
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Processing: {dataset_name}")
    print(f"{'='*80}")
    
    # Read input dataset
    print(f"📖 Reading dataset from {input_csv}...")
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    
    print(f"📊 Loaded {len(rows)} commit entries")
    
    # Add new columns if they don't exist
    new_columns = ['del_lines_of_words', 'del_complexity_score', 
                   'add_lines_of_words', 'add_complexity_score']
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)
    
    # Process each row
    print(f"\n🔄 Calculating metrics for deleted and added lines...")
    processed_rows = []
    
    for idx, row in enumerate(rows, 1):
        row.update(ReadabilityMetrics.commit_patch_metrics(row.get('patch_content', '')))
        
        processed_rows.append(row)
        
        # Progress update
        if idx % 1000 == 0:
            print(f"  Progress: {idx}/{len(rows)} commits processed")
        
        # Show sample for first few rows
        if idx <= 3:
            repo_info = f"{row['repository_owner']}/{row['repository_name']}"
            print(f"\n  📝 Sample [{idx}] {repo_info}")
            print(f"      Deleted: {row['del_lines_of_words']} words, "
                  f"complexity {row['del_complexity_score']}")
            print(f"      Added: {row['add_lines_of_words']} words, "
                  f"complexity {row['add_complexity_score']}")
    
    # Write output dataset
    print(f"\n💾 Writing updated dataset to {output_csv}...")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)
    
    print(f"\n✅ Processing complete!")
    print(f"   Total commits processed: {len(processed_rows)}")
    print(f"   Output saved to: {output_csv}")
    
    # Calculate and show statistics
    print(f"\n📈 Statistics:")
    total_del_words = sum(int(row['del_lines_of_words']) for row in processed_rows)
    total_add_words = sum(int(row['add_lines_of_words']) for row in processed_rows)
    avg_del_complexity = sum(float(row['del_complexity_score']) for row in processed_rows) / len(processed_rows) if processed_rows else 0
    avg_add_complexity = sum(float(row['add_complexity_score']) for row in processed_rows) / len(processed_rows) if processed_rows else 0
    
    print(f"   Total deleted words: {total_del_words:,}")
    print(f"   Total added words: {total_add_words:,}")
    print(f"   Avg deleted complexity: {avg_del_complexity:.2f}")
    print(f"   Avg added complexity: {avg_add_complexity:.2f}")


def main():
    """Main execution function."""
    print("="*80)
    print("Calculate Commit Metrics - Deleted vs Added Lines")
    print("="*80)
    print("\nThis script calculates word length and complexity scores for")
    print("deleted lines (prefix '-') and added lines (prefix '+') in commit patches.\n")
    
    for dataset in iter_manifest_datasets():
        if not dataset.commit_changes_path.exists():
            print(f"\n⚠️  Skipping {dataset.key}: File not found")
            print(f"    Expected: {dataset.commit_changes_path}")
            continue

        process_commit_dataset(
            str(dataset.commit_changes_path),
            str(dataset.commit_changes_path),
            f"{dataset.key} commit changes",
        )
    
    print("\n" + "="*80)
    print("🎉 All commit datasets processed successfully!")
    print("="*80)
    print("\nNew columns added:")
    print("  • del_lines_of_words - Word count for deleted lines")
    print("  • del_complexity_score - Flesch Reading Ease score for deleted lines")
    print("  • add_lines_of_words - Word count for added lines")
    print("  • add_complexity_score - Flesch Reading Ease score for added lines")
    print("\nUpdated files:")
    for dataset in iter_manifest_datasets():
        if dataset.commit_changes_path.exists():
            print(f"  • {dataset.commit_changes_path}")


if __name__ == "__main__":
    main()
