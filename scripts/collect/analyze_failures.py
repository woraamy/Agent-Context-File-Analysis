"""
Analyze failures in static dataset collection
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets

def analyze_failures(filepath, dataset_name):
    print(f"\n{'='*80}")
    print(f"Analyzing {dataset_name}")
    print(f"{'='*80}")
    
    total = 0
    success = 0
    failed = 0
    failed_entries = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get('static_content', '') == '':
                failed += 1
                failed_entries.append({
                    'owner': row.get('repository_owner', ''),
                    'repo': row.get('repository_name', ''),
                    'file': row.get('file_path', ''),
                    'url': row.get('file_url', '')
                })
            else:
                success += 1
    
    print(f"\n📊 Statistics:")
    print(f"   Total: {total}")
    print(f"   Success: {success} ({success/total*100:.1f}%)")
    print(f"   Failed: {failed} ({failed/total*100:.1f}%)")
    
    if failed_entries:
        print(f"\n❌ Failed entries (first 20):")
        for i, entry in enumerate(failed_entries[:20], 1):
            print(f"   {i}. {entry['owner']}/{entry['repo']}/{entry['file']}")
            if entry['url']:
                print(f"      URL: {entry['url']}")
    
    return total, success, failed

total_all = 0
success_all = 0
failed_all = 0

for dataset in iter_manifest_datasets():
    try:
        t, s, f = analyze_failures(dataset.static_path, f"{dataset.key} static dataset")
        total_all += t
        success_all += s
        failed_all += f
    except FileNotFoundError:
        print(f"\n❌ File not found: {dataset.static_path}")
    except Exception as e:
        print(f"\n❌ Error processing {dataset.static_path}: {e}")

print(f"\n{'='*80}")
print(f"OVERALL SUMMARY")
print(f"{'='*80}")
print(f"Total files: {total_all}")
print(f"Successful: {success_all} ({success_all/total_all*100:.1f}%)")
print(f"Failed: {failed_all} ({failed_all/total_all*100:.1f}%)")
