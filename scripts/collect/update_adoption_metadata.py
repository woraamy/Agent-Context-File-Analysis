from __future__ import annotations

import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets

def update_metadata():
    print("Starting metadata update for adoption datasets...")
    for dataset in iter_manifest_datasets():
        adoption_file = dataset.adoption_commits_path
        main_file = dataset.original_path
        
        if not adoption_file.exists():
            print(f"Skipping {dataset.key}: Adoption file not found ({adoption_file})")
            continue
        
        if not main_file.exists():
            print(f"Skipping {dataset.key}: Main dataset file not found ({main_file})")
            continue
            
        print(f"Processing {dataset.key}...")
        
        try:
            # Read datasets
            df_adoption = pd.read_csv(adoption_file)
            df_main = pd.read_csv(main_file)
            
            # Prepare main dataset subset for merging
            # We want to match on owner/name and bring in url/path
            cols_to_merge = ['repository_owner', 'repository_name', 'repository_url', 'file_path', 'file_url']
            
            # Verify columns exist in main dataset
            missing_cols = [c for c in cols_to_merge if c not in df_main.columns]
            if missing_cols:
                print(f"  Error: Main dataset missing columns {missing_cols}")
                continue

            df_metadata = df_main[cols_to_merge].drop_duplicates()
            
            # If target columns already exist in adoption dataset, drop them to avoid duplication/suffixed columns
            if 'repository_url' in df_adoption.columns:
                df_adoption = df_adoption.drop(columns=['repository_url'])
            if 'file_path' in df_adoption.columns:
                df_adoption = df_adoption.drop(columns=['file_path'])
            if 'file_url' in df_adoption.columns:
                df_adoption = df_adoption.drop(columns=['file_url'])

            # Merge
            # keeping all rows from adoption dataset (left join)
            df_updated = pd.merge(
                df_adoption, 
                df_metadata, 
                on=['repository_owner', 'repository_name'], 
                how='left'
            )
            
            # Reorder columns to place new metadata near the start (after names)
            cols = list(df_updated.columns)
            base_cols = ['repository_owner', 'repository_name']
            new_cols = ['repository_url', 'file_path', 'file_url']
            other_cols = [c for c in cols if c not in base_cols and c not in new_cols]
            
            final_order = base_cols + new_cols + other_cols
            df_updated = df_updated[final_order]
            
            # Save back
            df_updated.to_csv(adoption_file, index=False)
            print(f"  Successfully updated {adoption_file}")
            print(f"  Added metadata for {len(df_updated)} rows.")
            
        except Exception as e:
            print(f"  Error updating {dataset.key}: {e}")

if __name__ == "__main__":
    update_metadata()
