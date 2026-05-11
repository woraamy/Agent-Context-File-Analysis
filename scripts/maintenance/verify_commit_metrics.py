"""
Verify and display statistics for the newly added commit metrics
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets

def analyze_commit_metrics(csv_path, dataset_name):
    """Analyze the newly added metrics in a commit dataset."""
    print(f"\n{'='*80}")
    print(f"Analysis: {dataset_name}")
    print(f"{'='*80}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Check columns exist
    required_cols = ['del_lines_of_words', 'del_complexity_score', 
                     'add_lines_of_words', 'add_complexity_score']
    
    missing_cols = [col for col in required_cols if col not in reader.fieldnames]
    if missing_cols:
        print(f"❌ Missing columns: {missing_cols}")
        return
    
    print(f"✅ All required columns present")
    print(f"📊 Total commits: {len(rows)}")
    
    # Calculate statistics
    commits_with_deletions = sum(1 for r in rows if int(r['del_lines_of_words']) > 0)
    commits_with_additions = sum(1 for r in rows if int(r['add_lines_of_words']) > 0)
    
    total_del_words = sum(int(r['del_lines_of_words']) for r in rows)
    total_add_words = sum(int(r['add_lines_of_words']) for r in rows)
    
    del_scores = [float(r['del_complexity_score']) for r in rows if float(r['del_complexity_score']) != 0]
    add_scores = [float(r['add_complexity_score']) for r in rows if float(r['add_complexity_score']) != 0]
    
    avg_del_complexity = sum(del_scores) / len(del_scores) if del_scores else 0
    avg_add_complexity = sum(add_scores) / len(add_scores) if add_scores else 0
    
    print(f"\n📈 Deleted Lines:")
    print(f"   Commits with deletions: {commits_with_deletions} ({commits_with_deletions/len(rows)*100:.1f}%)")
    print(f"   Total words deleted: {total_del_words:,}")
    print(f"   Avg words per commit: {total_del_words/len(rows):.1f}")
    print(f"   Avg complexity: {avg_del_complexity:.2f}")
    
    print(f"\n📈 Added Lines:")
    print(f"   Commits with additions: {commits_with_additions} ({commits_with_additions/len(rows)*100:.1f}%)")
    print(f"   Total words added: {total_add_words:,}")
    print(f"   Avg words per commit: {total_add_words/len(rows):.1f}")
    print(f"   Avg complexity: {avg_add_complexity:.2f}")
    
    # Show some sample rows
    print(f"\n📝 Sample rows with both deletions and additions:")
    count = 0
    for row in rows:
        if int(row['del_lines_of_words']) > 0 and int(row['add_lines_of_words']) > 0:
            print(f"\n   {row['repository_owner']}/{row['repository_name']}")
            print(f"   Deleted: {row['del_lines_of_words']} words, complexity {row['del_complexity_score']}")
            print(f"   Added: {row['add_lines_of_words']} words, complexity {row['add_complexity_score']}")
            count += 1
            if count >= 3:
                break

def main():
    print("="*80)
    print("Commit Metrics Verification")
    print("="*80)
    
    for dataset in iter_manifest_datasets():
        csv_path = dataset.commit_changes_path
        if csv_path.exists():
            analyze_commit_metrics(csv_path, f"{dataset.key} commit changes")
        else:
            print(f"\n⚠️  File not found: {csv_path}")
    
    print("\n" + "="*80)
    print("✅ Verification complete!")
    print("="*80)

if __name__ == "__main__":
    main()
