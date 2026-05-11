"""Recalculate original-dataset readability fields from static content."""

from __future__ import annotations

import csv
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.readability import ReadabilityMetrics


def create_file_key(owner, repo, file_url):
    """Create a unique key for matching files across datasets."""
    return ReadabilityMetrics.create_file_key(owner, repo, file_url)


def update_metrics_in_original(original_csv, static_csv, output_csv, dataset_name):
    """
    Recalculate length_of_words and complexity_score from static content
    and update the original dataset.
    
    Args:
        original_csv: Path to original dataset
        static_csv: Path to static dataset with static_content
        output_csv: Path to save updated original dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Updating Metrics: {dataset_name}")
    print(f"{'='*80}")
    
    # Read static dataset to get static_content
    static_data = {}
    print(f"📖 Reading static dataset...")
    with open(static_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = create_file_key(row['repository_owner'], row['repository_name'], row['file_url'])
            static_data[key] = {
                'static_content': row.get('static_content', ''),
                'original_length': row.get('length_of_words', ''),
                'original_complexity': row.get('complexity_score', '')
            }
    
    print(f"📊 Loaded {len(static_data)} entries from static dataset")
    
    # Read original dataset
    print(f"📖 Reading original dataset...")
    with open(original_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        original_rows = list(reader)
    
    print(f"📊 Loaded {len(original_rows)} entries from original dataset")
    
    # Verify columns exist
    if 'length_of_words' not in fieldnames or 'complexity_score' not in fieldnames:
        print("❌ Error: length_of_words or complexity_score column not found!")
        return
    
    # Recalculate metrics
    print(f"\n🔄 Recalculating metrics from static content...")
    updated_rows = []
    recalculated = 0
    unchanged = 0
    significant_changes = 0
    
    for idx, row in enumerate(original_rows, 1):
        key = create_file_key(row['repository_owner'], row['repository_name'], row['file_url'])
        
        if key in static_data:
            static_content = static_data[key]['static_content']
            old_length = row.get('length_of_words', '')
            old_complexity = row.get('complexity_score', '')
            
            # Recalculate metrics
            new_length = ReadabilityMetrics.calculate_length_of_words(static_content)
            new_complexity = ReadabilityMetrics.calculate_complexity_score(static_content)
            
            # Update row
            row['length_of_words'] = new_length
            row['complexity_score'] = new_complexity
            
            recalculated += 1
            
            # Check for significant changes
            try:
                if old_length and abs(float(old_length) - new_length) > 100:
                    significant_changes += 1
                    if significant_changes <= 5:  # Show first 5
                        print(f"  📝 [{idx}] {row['repository_owner']}/{row['repository_name']}")
                        print(f"      Length: {old_length} → {new_length}")
                        print(f"      Complexity: {old_complexity} → {new_complexity:.2f}")
            except (ValueError, TypeError):
                pass
            
        else:
            unchanged += 1
            print(f"  ⚠️  [{idx}] Not found in static data: {row['repository_owner']}/{row['repository_name']}")
        
        updated_rows.append(row)
        
        # Progress update
        if idx % 100 == 0:
            print(f"  Progress: {idx}/{len(original_rows)} ({recalculated} recalculated)")
    
    # Write updated dataset
    print(f"\n💾 Writing updated dataset...")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    print(f"\n✅ Update complete!")
    print(f"   Recalculated: {recalculated}/{len(original_rows)}")
    print(f"   Unchanged: {unchanged}/{len(original_rows)}")
    print(f"   Significant changes: {significant_changes}")
    print(f"   Output: {output_csv}")


def main():
    """Main execution function."""
    print("="*80)
    print("Recalculate Metrics from Static Content")
    print("="*80)
    print("\nThis script recalculates length_of_words and complexity_score")
    print("based on the actual static_content retrieved from GitHub.\n")
    
    for dataset in iter_manifest_datasets():
        update_metrics_in_original(
            str(dataset.original_path),
            str(dataset.static_path),
            str(dataset.original_path),
            f"{dataset.key} dataset"
        )
    
    print("\n" + "="*80)
    print("🎉 All metrics recalculated successfully!")
    print("="*80)
    print("\nUpdated files:")
    for dataset in iter_manifest_datasets():
        print(f"  ✅ {dataset.original_path}")
    
    print("\nMetrics Updated:")
    print("  • length_of_words - Total word count (excluding code blocks)")
    print("  • complexity_score - Flesch Reading Ease score")


if __name__ == "__main__":
    main()
