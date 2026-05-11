from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.utils.paths import DERIVED_MANUAL_INSPECTION_DIR, DERIVED_RESEARCH_DIR, ensure_dir

def count_conflicts():
    # Read both datasets
    amy_path = DERIVED_MANUAL_INSPECTION_DIR / "amy_dataset.csv"
    aj_path = DERIVED_MANUAL_INSPECTION_DIR / "aj_tem_dataset.csv"
    
    amy_df = pd.read_csv(amy_path)
    aj_df = pd.read_csv(aj_path)
    
    # List to store results for CSV output
    results = []
    
    # Get label columns (Label1 through Label15)
    label_cols = [f'Label{i}' for i in range(1, 16)]
    
    # Print header
    print("=" * 80)
    print("LABEL CONFLICT ANALYSIS")
    print("=" * 80)
    print(f"Comparing: amy_dataset.csv vs aj_tem_dataset.csv")
    print("=" * 80)
    print()
    
    total_conflicts = 0
    total_labels_sum = 0
    rows_compared = 0
    
    # Iterate through rows and compare
    for idx, amy_row in amy_df.iterrows():
        row_num = amy_row['#']
        
        # Find matching row in aj_tem dataset
        aj_row = aj_df[aj_df['#'] == row_num]
        
        if aj_row.empty:
            print(f"Row #{row_num}: Not found in aj_tem_dataset - SKIPPED")
            continue
        
        aj_row = aj_row.iloc[0]
        
        # Get all labels from both datasets as sets (ignore order)
        amy_labels = set()
        aj_labels = set()
        
        for label_col in label_cols:
            amy_val = amy_row[label_col] if pd.notna(amy_row[label_col]) else ""
            aj_val = aj_row[label_col] if pd.notna(aj_row[label_col]) else ""
            
            if amy_val.strip():
                amy_labels.add(amy_val.strip())
            if aj_val.strip():
                aj_labels.add(aj_val.strip())
        
        # Find labels that are in one set but not the other
        only_in_amy = amy_labels - aj_labels
        only_in_aj = aj_labels - amy_labels
        
        # Total unique labels (union of both sets)
        all_unique_labels = amy_labels | aj_labels
        total_labels = len(all_unique_labels)
        
        # Conflicts are labels that appear in only one dataset
        conflicts = len(only_in_amy) + len(only_in_aj)
        
        # Calculate disagreement percentage
        disagreement_pct = (conflicts / total_labels * 100) if total_labels > 0 else 0
        
        # Common labels
        common_labels = amy_labels & aj_labels
        
        # Store result for CSV
        results.append({
            'row_number': row_num,
            'repository_owner': amy_row['repository_owner'],
            'repository_name': amy_row['repository_name'],
            'file_url': amy_row['file_url'],
            'conflicts': conflicts,
            'total_labels': total_labels,
            'disagreement_percentage': round(disagreement_pct, 2),
            'amy_label_count': len(amy_labels),
            'tem_label_count': len(aj_labels),
            'common_label_count': len(common_labels),
            'only_in_amy': '; '.join(sorted(only_in_amy)) if only_in_amy else '',
            'only_in_tem': '; '.join(sorted(only_in_aj)) if only_in_aj else '',
            'common_labels': '; '.join(sorted(common_labels)) if common_labels else ''
        })
        
        # Print result for this row
        repo_name = f"{amy_row['repository_owner']}/{amy_row['repository_name']}"
        print(f"Row #{row_num}: {repo_name}")
        print(f"  Conflicts: {conflicts} out of {total_labels} labels")
        
        if conflicts > 0:
            print("  Details:")
            if only_in_amy:
                print(f"    Only in Amy: {', '.join(sorted(only_in_amy))}")
            if only_in_aj:
                print(f"    Only in Aj: {', '.join(sorted(only_in_aj))}")
            if common_labels:
                print(f"    Common labels: {', '.join(sorted(common_labels))}")
        
        print()
        
        total_conflicts += conflicts
        total_labels_sum += total_labels
        rows_compared += 1
    
    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total rows compared: {rows_compared}")
    print(f"Total conflicts: {total_conflicts}")
    print(f"Total labels: {total_labels_sum}")
    if total_labels_sum > 0:
        conflict_rate = (total_conflicts / total_labels_sum) * 100
        print(f"Conflict rate: {conflict_rate:.2f}%")
    print("=" * 80)
    
    # Save results to CSV
    results_df = pd.DataFrame(results)
    ensure_dir(DERIVED_RESEARCH_DIR)
    output_path = DERIVED_RESEARCH_DIR / "label_disagreement_analysis.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")
    print(f"Total rows saved: {len(results_df)}")
    
    # Print some statistics
    print("\n" + "=" * 80)
    print("DISAGREEMENT STATISTICS")
    print("=" * 80)
    print(f"Average disagreement: {results_df['disagreement_percentage'].mean():.2f}%")
    print(f"Median disagreement: {results_df['disagreement_percentage'].median():.2f}%")
    print(f"Min disagreement: {results_df['disagreement_percentage'].min():.2f}%")
    print(f"Max disagreement: {results_df['disagreement_percentage'].max():.2f}%")
    print(f"Rows with 0% disagreement: {len(results_df[results_df['disagreement_percentage'] == 0])}")
    print(f"Rows with 100% disagreement: {len(results_df[results_df['disagreement_percentage'] == 100])}")
    print("=" * 80)

if __name__ == "__main__":
    count_conflicts()
