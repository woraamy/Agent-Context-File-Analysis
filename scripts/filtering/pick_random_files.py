#!/usr/bin/env python3
"""
Script to randomly pick files from each dataset:
- 3 files from agents_dataset.csv
- 4 files from claude_dataset.csv
- 2 files from copilot-instructions_dataset.csv

Total: 9 files saved to datasets/derived/manual_inspection/added_random_files.csv
"""

from __future__ import annotations

import pandas as pd
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.paths import DERIVED_MANUAL_INSPECTION_DIR, ensure_dir

# Configuration
RANDOM_STATE = 42  # For reproducibility
OUTPUT_FILE = DERIVED_MANUAL_INSPECTION_DIR / "added_random_files.csv"

# Define how many files to pick from each dataset
SAMPLE_COUNTS = {
    'agents': 3,
    'claude': 4,
    'copilot-instructions': 2
}

# Dataset file paths
DATASET_FILES = {
    'agents': get_manifest_dataset('agents').original_path,
    'claude': get_manifest_dataset('claude').original_path,
    'copilot-instructions': get_manifest_dataset('copilot-instructions').original_path,
}


def main():
    print("=" * 80)
    print("RANDOMLY PICKING FILES FROM DATASETS")
    print("=" * 80)
    
    all_samples = []
    
    for dataset_name, sample_count in SAMPLE_COUNTS.items():
        dataset_file = DATASET_FILES[dataset_name]
        
        if not dataset_file.exists():
            print(f"❌ Error: File not found: {dataset_file}")
            continue
        
        # Load the dataset
        print(f"\n📂 Loading {dataset_name} dataset...")
        df = pd.read_csv(dataset_file)
        print(f"   Total files available: {len(df)}")
        
        # Randomly sample
        if len(df) < sample_count:
            print(f"⚠️  Warning: Only {len(df)} files available, requesting {sample_count}")
            sample_count = len(df)
        
        sampled = df.sample(n=sample_count, random_state=RANDOM_STATE)
        print(f"✅ Randomly picked {len(sampled)} files")
        
        # Add source_dataset column for tracking
        sampled = sampled.copy()
        sampled['source_dataset'] = dataset_name
        
        all_samples.append(sampled)
    
    # Combine all samples
    if not all_samples:
        print("\n❌ No samples collected. Exiting.")
        return
    
    final_df = pd.concat(all_samples, ignore_index=True)
    
    # Save to output file
    print(f"\n💾 Saving {len(final_df)} files to {OUTPUT_FILE}...")
    ensure_dir(OUTPUT_FILE.parent)
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Successfully saved!")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files selected: {len(final_df)}")
    for dataset_name in SAMPLE_COUNTS.keys():
        count = len(final_df[final_df['source_dataset'] == dataset_name])
        print(f"  - {dataset_name}: {count} files")
    
    print(f"\nOutput saved to: {OUTPUT_FILE}")
    
    # Show sample of selected files
    print("\n📋 Sample of selected files:")
    for idx, row in final_df.head(5).iterrows():
        print(f"  {idx+1}. {row['repository_owner']}/{row['repository_name']} ({row['source_dataset']})")
    if len(final_df) > 5:
        print(f"  ... and {len(final_df) - 5} more")


if __name__ == "__main__":
    main()
