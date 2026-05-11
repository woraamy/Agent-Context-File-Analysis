from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from cliffs_delta import cliffs_delta # Requires 'pip install cliffs-delta'
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.utils.paths import DERIVED_CLASSIFICATION_DIR, DERIVED_STATISTICS_DIR, ensure_dir

def mannUandCliffdelta(dist1, dist2):
    """
    Performs Mann-Whitney U test and calculates Cliff's Delta.
    """
    try:
        # 1. Calculate Cliff's Delta
        d, size = cliffs_delta(dist1, dist2)

        # 2. Calculate Mann-Whitney U
        # For binary data (0/1), this compares the proportion of 1s in the distributions
        u, p = stats.mannwhitneyu(dist1, dist2, alternative="two-sided")

        return u, p, d, size
    except Exception as e:
        return None, None, 0, "Error"

def analyze_labels_by_source():
    # Define file path
    input_file = DERIVED_CLASSIFICATION_DIR / "inputs" / "final_am_classification_3.csv"
    
    if not input_file.exists():
        print(f"Error: File not found at {input_file}")
        return

    # Load the classification data
    df = pd.read_csv(input_file)
    
    # Identify label columns (assuming they start with 'Label')
    label_cols = [col for col in df.columns if col.startswith('Label')]
    
    if not label_cols:
        print("Error: No label columns found.")
        return

    # Normalize source_dataset names if needed (e.g., lowercasing)
    df['source_dataset'] = df['source_dataset'].str.strip().str.lower()
    
    # 1. Melt the dataframe to have one row per label instance
    # This transforms: ID, Source, Label1=A, Label2=B
    # Into: 
    #   ID, Source, Label=A
    #   ID, Source, Label=B
    melted_df = df.melt(
        id_vars=['repository_owner', 'repository_name', 'source_dataset'], 
        value_vars=label_cols, 
        value_name='Category'
    ).dropna(subset=['Category']) # Drop rows where Category is NaN (unused label slots)

    # 2. Compute counts per source and category
    # Group by Source and Category
    stats = melted_df.groupby(['source_dataset', 'Category']).size().reset_index(name='Count')
    
    # 3. Calculate percentages per source
    # First, get total labels count per source for normalization
    source_totals = melted_df.groupby('source_dataset').size().reset_index(name='Total_Labels')
    
    stats = stats.merge(source_totals, on='source_dataset')
    stats['Percentage'] = (stats['Count'] / stats['Total_Labels'] * 100).round(2)
    
    # 4. Display results
    print("="*60)
    print("Label Statistics by Source Dataset")
    print("="*60)
    
    sources = stats['source_dataset'].unique()
    
    for source in sorted(sources):
        print(f"\n--- Source: {source} ---")
        source_data = stats[stats['source_dataset'] == source].sort_values('Count', ascending=False)
        print(source_data[['Category', 'Count', 'Percentage']].to_string(index=False))
        print(f"Total Labels: {source_totals[source_totals['source_dataset'] == source]['Total_Labels'].values[0]}")

    # 5. Create a pivot table for easier comparison (Optional export)
    pivot_table = stats.pivot(index='Category', columns='source_dataset', values=['Count', 'Percentage'])
    print("\n" + "="*60)
    print("Comparison Pivot Table (Percentage)")
    print("="*60)
    # Filling NaNs with 0 for categories present in some but not all sources
    print(pivot_table['Percentage'].fillna(0).to_string())

    # 6. (Optional) Save to CSV
    ensure_dir(DERIVED_STATISTICS_DIR)
    output_path = DERIVED_STATISTICS_DIR / "label_distribution_by_source.csv"
    pivot_table.to_csv(output_path)
    print(f"\nSaved detailed pivot statistics to {output_path}")

    # 7. Perform Significance Tests
    print("\n" + "="*60)
    print("Significance Tests (Mann-Whitney U & Cliff's Delta)")
    print("="*60)
    
    # We need to restructure data to binary matrix: Rows=files, Cols=Categories, Value=1 if present, 0 if not
    # This allows us to compare "Prevalence of Label A in Source 1" vs "Prevalence of Label A in Source 2"
    
    # Create binary representation
    binary_data = []
    
    # Iterate through original dataframe to build binary rows per file
    for idx, row in df.iterrows():
        source = row['source_dataset']
        # Collect all labels for this file
        file_labels = set()
        for col in label_cols:
            val = row[col]
            if pd.notna(val) and isinstance(val, str):
                file_labels.add(val)
        
        # Create a dictionary for this file
        row_dict = {'source_dataset': source}
        
        # For every known category, mark 1 if present in this file, 0 otherwise
        all_categories = melted_df['Category'].unique()
        for cat in all_categories:
            row_dict[cat] = 1 if cat in file_labels else 0
            
        binary_data.append(row_dict)
        
    binary_df = pd.DataFrame(binary_data)
    
    # Pairwise comparison of sources
    unique_sources = binary_df['source_dataset'].unique()
    categories = melted_df['Category'].unique()
    
    sig_results = []

    for i in range(len(unique_sources)):
        for j in range(i + 1, len(unique_sources)):
            s1 = unique_sources[i]
            s2 = unique_sources[j]
            
            print(f"\nComparing {s1} vs {s2}")
            print("-" * 40)
            
            df1 = binary_df[binary_df['source_dataset'] == s1]
            df2 = binary_df[binary_df['source_dataset'] == s2]
            
            for cat in sorted(categories):
                dist1 = df1[cat].values
                dist2 = df2[cat].values
                
                # Minimum data check
                if len(dist1) > 0 and len(dist2) > 0 and (sum(dist1) > 0 or sum(dist2) > 0):
                    u, p, d, size = mannUandCliffdelta(dist1, dist2)
                    
                    if p is not None:
                        sig_results.append({
                            'Comparison': f"{s1} vs {s2}",
                            'Category': cat,
                            'P-value': p,
                            'Cliff\'s d': d,
                            'Effect Size': size
                        })
                        
                        # Print only if significant (p < 0.05) or large effect for cleanliness
                        if p < 0.05:
                            print(f"{cat:25}: p={p:.4f}, d={d:.2f} ({size}) *")
                        else:
                            # Uncomment to see all
                            # print(f"{cat:25}: p={p:.4f}, d={d:.2f} ({size})")
                            pass
                
    # Save significance results
    if sig_results:
        sig_df = pd.DataFrame(sig_results)
        sig_path = DERIVED_STATISTICS_DIR / "label_significance_results.csv"
        sig_df.to_csv(sig_path, index=False)
        print(f"\nSaved significance test results to {sig_path}")

if __name__ == "__main__":
    analyze_labels_by_source()
