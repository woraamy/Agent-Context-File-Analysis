from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.paths import (
    DERIVED_CLASSIFICATION_DIR,
    DERIVED_MANUAL_INSPECTION_DIR,
    ensure_dir,
)

# --- Configuration ---
MANUAL_CLASSIFICATION_FILE = DERIVED_CLASSIFICATION_DIR / "inputs" / "final_am_classification_3.csv"
OUTPUT_FILE = DERIVED_MANUAL_INSPECTION_DIR / "same_entries.csv"

# Dataset files to read
DATASET_FILES = list(iter_manifest_datasets())


def create_comparable_path(row):
    """
    Creates a comparable path format from dataset row.
    Format: owner/repo/filename
    """
    return f"{row['repository_owner']}/{row['repository_name']}/{row['filename']}"


def extract_path_from_url(file_url):
    """
    Extracts owner/repo/filename from a GitHub URL.
    Example: https://github.com/google/adk-python/blob/.../AGENTS.md -> google/adk-python/AGENTS.md
    """
    try:
        # Remove the base GitHub URL and split
        # Format: https://github.com/owner/repo/blob/commit_hash/filename
        parts = file_url.replace('https://github.com/', '').split('/')
        if len(parts) >= 4:
            owner = parts[0]
            repo = parts[1]
            # Skip 'blob' and commit hash, get filename (last part)
            filename = parts[-1]
            return f"{owner}/{repo}/{filename}"
    except Exception as e:
        print(f"  Warning: Could not parse URL: {file_url} - {e}")
    return None


def match_datasets_with_manual_classification():
    """
    Reads the three dataset files and matches entries with manual_classification_am.csv
    based on repository_owner, repository_name, and filename.
    """
    print("=" * 60)
    print("MATCHING DATASET ENTRIES WITH MANUAL CLASSIFICATION")
    print("=" * 60)
    
    # 1. Load manual classification file
    if not os.path.exists(MANUAL_CLASSIFICATION_FILE):
        print(f"✗ Error: Manual classification file not found: {MANUAL_CLASSIFICATION_FILE}")
        return
    
    print(f"\n📖 Reading manual classification file...")
    df_manual = pd.read_csv(MANUAL_CLASSIFICATION_FILE)
    print(f"   Found {len(df_manual)} entries in manual classification")
    
    # Create a set of comparable paths from manual classification
    # Extract owner/repo/filename from file_url
    df_manual['comparable_path'] = df_manual['file_url'].apply(extract_path_from_url)
    manual_paths = set(df_manual['comparable_path'].dropna())
    print(f"   Extracted {len(manual_paths)} unique paths from manual classification")
    
    # 2. Load and combine all dataset files
    all_matching_entries = []
    
    for dataset_file in DATASET_FILES:
        dataset_path = dataset_file.original_path
        
        if not dataset_path.exists():
            print(f"\n⚠️  Skipping {dataset_file.key}: File not found")
            continue
        
        print(f"\n📊 Processing {dataset_file.key}...")
        df_dataset = pd.read_csv(dataset_path)
        print(f"   Total entries: {len(df_dataset)}")
        
        # Create comparable paths for this dataset
        df_dataset['comparable_path'] = df_dataset.apply(create_comparable_path, axis=1)
        
        # Find matches
        df_dataset['is_match'] = df_dataset['comparable_path'].isin(manual_paths)
        matches = df_dataset[df_dataset['is_match']]
        
        # Add source dataset column
        matches = matches.copy()
        matches['source_dataset'] = dataset_file.key
        
        print(f"   ✓ Found {len(matches)} matching entries")
        
        if len(matches) > 0:
            all_matching_entries.append(matches)
    
    # 3. Combine all matches
    if not all_matching_entries:
        print("\n✗ No matching entries found across any datasets")
        return
    
    df_combined = pd.concat(all_matching_entries, ignore_index=True)
    
    # 4. Merge with manual classification to get labels
    print(f"\n🔗 Merging with manual classification data...")
    df_combined = df_combined.merge(
        df_manual,
        on='comparable_path',
        how='left',
        suffixes=('', '_manual')
    )
    
    # 5. Clean up columns - remove duplicate columns and temporary ones
    # Keep the dataset columns and add the label columns from manual classification
    label_columns = [col for col in df_manual.columns if col.startswith('Label') or col == 'Note' or col == 'ID']
    
    # Select columns to keep
    dataset_columns = [col for col in df_combined.columns if not col.endswith('_manual') and col != 'is_match']
    columns_to_keep = dataset_columns + [col for col in label_columns if col in df_combined.columns]
    
    df_combined = df_combined[columns_to_keep]
    
    # 6. Save to output file
    ensure_dir(OUTPUT_FILE.parent)
    df_combined.to_csv(OUTPUT_FILE, index=False)
    
    # 7. Print summary
    print(f"\n" + "=" * 60)
    print(f"✅ MATCHING COMPLETE")
    print(f"=" * 60)
    print(f"Total matching entries: {len(df_combined)}")
    print(f"Breakdown by source:")
    print(df_combined['source_dataset'].value_counts().to_string())
    print(f"\n📁 Output saved to: {OUTPUT_FILE}")
    print("=" * 60)


# --- Execution Block ---
if __name__ == "__main__":
    match_datasets_with_manual_classification()
