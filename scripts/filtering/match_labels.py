"""
Match same_entries.csv with manual classification files and preserve labels.

This script:
1. Reads same_entries.csv
2. Matches with manual_classification_am.csv and manual_calssification_am_v2.csv
3. Keeps the labels from the manual classification files
4. Outputs matched entries to datasets/same_entries_am.csv and datasets/same_entries_v2.csv
"""

from __future__ import annotations

import pandas as pd
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.utils.paths import DERIVED_CLASSIFICATION_DIR, DERIVED_MANUAL_INSPECTION_DIR

def parse_file_url_to_path(file_url):
    """Extract owner/repo/filename from GitHub URL for matching."""
    if pd.isna(file_url) or not file_url:
        return None
    
    # Example: https://github.com/google/adk-python/blob/ad81aa54de1f38df580915b7f47834ea8e5f1004/AGENTS.md
    # or: https://github.com/bloxbean/yaci/blob/29b1412d3e60ed132afd4cd60dd9d4479584e9fe/docs/agents.md
    try:
        parts = file_url.split('/')
        if len(parts) >= 7:
            owner = parts[3]
            repo = parts[4]
            # Get filename - everything after the commit hash
            filename_parts = parts[7:]
            filename = '/'.join(filename_parts)
            return f"{owner}/{repo}/{filename}"
    except Exception as e:
        print(f"Error parsing URL {file_url}: {e}")
    
    return None

def match_with_manual_classification(same_entries_df, manual_class_df, id_column='ID'):
    """
    Match same_entries with manual classification and preserve labels.
    
    Args:
        same_entries_df: DataFrame from same_entries.csv
        manual_class_df: DataFrame from manual classification file
        id_column: Name of the ID column in manual classification ('ID' or '#')
    
    Returns:
        DataFrame with matched entries in manual classification format
    """
    matched_entries = []
    
    # Create lookup dictionaries for faster matching
    manual_lookup = {}
    for _, row in manual_class_df.iterrows():
        file_path = parse_file_url_to_path(row['file_url'])
        if file_path:
            manual_lookup[file_path] = row
    
    print(f"Manual classification entries: {len(manual_class_df)}")
    print(f"Manual lookup keys created: {len(manual_lookup)}")
    
    # Match same_entries with manual classification
    for _, entry in same_entries_df.iterrows():
        # Try to match using file_url from same_entries
        entry_path = parse_file_url_to_path(entry.get('file_url'))
        
        if entry_path and entry_path in manual_lookup:
            manual_row = manual_lookup[entry_path]
            
            # Create a new row with manual classification format
            matched_row = {
                id_column: manual_row[id_column],
                'repository_owner': entry['repository_owner'],
                'repository_name': entry['repository_name'],
                'source_dataset': entry['source_dataset'],
                'stargazers_count': entry['stargazers_count'],
                'total_repo_commits_after_manifest_initialization': entry.get('total_repo_commits_after_manifest_initialization', ''),
                'Note': manual_row.get('Note', ''),
                'file_url': entry['file_url'],
            }
            
            # Add all label columns
            for i in range(1, 16):
                label_col = f'Label{i}'
                matched_row[label_col] = manual_row.get(label_col, '')
            
            matched_entries.append(matched_row)
            print(f"✓ Matched: {entry['repository_owner']}/{entry['repository_name']}")
        else:
            print(f"✗ Not found in manual classification: {entry.get('repository_owner')}/{entry.get('repository_name')} - {entry_path}")
    
    print(f"\nTotal matched entries: {len(matched_entries)}")
    
    if matched_entries:
        return pd.DataFrame(matched_entries)
    else:
        return pd.DataFrame()

def main():
    # Define file paths
    same_entries_path = DERIVED_MANUAL_INSPECTION_DIR / 'same_entries.csv'
    manual_am_path = DERIVED_CLASSIFICATION_DIR / 'inputs' / 'final_am_classification_3.csv'
    manual_v2_path = DERIVED_CLASSIFICATION_DIR / 'inputs' / 'manual_calssification_am_v2.csv'
    
    output_am_path = DERIVED_MANUAL_INSPECTION_DIR / 'same_entries_am.csv'
    output_v2_path = DERIVED_MANUAL_INSPECTION_DIR / 'same_entries_v2.csv'
    
    print("=" * 80)
    print("Loading data files...")
    print("=" * 80)
    
    # Load same_entries.csv
    print(f"\nLoading {same_entries_path}...")
    same_entries_df = pd.read_csv(same_entries_path)
    print(f"Loaded {len(same_entries_df)} entries from same_entries.csv")
    
    # Load manual classification files
    print(f"\nLoading {manual_am_path}...")
    manual_am_df = pd.read_csv(manual_am_path)
    print(f"Loaded {len(manual_am_df)} entries from manual_classification_am.csv")
    
    print(f"\nLoading {manual_v2_path}...")
    manual_v2_df = pd.read_csv(manual_v2_path)
    print(f"Loaded {len(manual_v2_df)} entries from manual_calssification_am_v2.csv")
    
    # Match with manual_classification_am.csv
    print("\n" + "=" * 80)
    print("Matching with manual_classification_am.csv...")
    print("=" * 80)
    same_entries_am = match_with_manual_classification(
        same_entries_df, 
        manual_am_df,
        id_column='ID'
    )
    
    # Match with manual_calssification_am_v2.csv
    print("\n" + "=" * 80)
    print("Matching with manual_calssification_am_v2.csv...")
    print("=" * 80)
    same_entries_v2 = match_with_manual_classification(
        same_entries_df,
        manual_v2_df,
        id_column='#'
    )
    
    # Save results
    print("\n" + "=" * 80)
    print("Saving results...")
    print("=" * 80)
    
    if not same_entries_am.empty:
        same_entries_am.to_csv(output_am_path, index=False)
        print(f"\n✅ Saved {len(same_entries_am)} entries to {output_am_path}")
        print(f"Columns: {list(same_entries_am.columns)}")
    else:
        print(f"\n⚠️  No matches found for manual_classification_am.csv")
    
    if not same_entries_v2.empty:
        same_entries_v2.to_csv(output_v2_path, index=False)
        print(f"\n✅ Saved {len(same_entries_v2)} entries to {output_v2_path}")
        print(f"Columns: {list(same_entries_v2.columns)}")
    else:
        print(f"\n⚠️  No matches found for manual_calssification_am_v2.csv")
    
    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)
    print(f"Same entries total: {len(same_entries_df)}")
    print(f"Matched with manual_classification_am: {len(same_entries_am)}")
    print(f"Matched with manual_calssification_am_v2: {len(same_entries_v2)}")
    print("\nDone! ✨")

if __name__ == '__main__':
    main()
