import pandas as pd
import numpy as np
from scipy import stats
from cliffs_delta import cliffs_delta # Requires 'pip install cliffs-delta'
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset

def mannUandCliffdelta(dist1, dist2):
    """
    Performs Mann-Whitney U test and calculates Cliff's Delta.

    Note: This function assumes dist1 and dist2 are lists/arrays
    with NaN values already removed.
    """
    # 1. Calculate Cliff's Delta
    # The cliffs_delta library function handles lists/arrays
    d, size = cliffs_delta(dist1, dist2)

    # 2. Calculate Mann-Whitney U
    u, p = stats.mannwhitneyu(dist1, dist2, alternative="two-sided")

    # 3. Print results as defined in your function
    print(f"    Cliff's delta: size={size}, d={round(d, 2)}")
    print(f"    Mann-Whitney-U-test: u={round(u, 2)} p={p:.6f}")

    return u, p, d, size

def load_data():
    """Loads the adoption datasets."""
    try:
        agents_df = pd.read_csv(get_manifest_dataset('agents').tool_only_adoption_path)
        claude_df = pd.read_csv(get_manifest_dataset('claude').tool_only_adoption_path)
        copilot_df = pd.read_csv(get_manifest_dataset('copilot-instructions').tool_only_adoption_path)
        
        return agents_df, claude_df, copilot_df
    except FileNotFoundError as e:
        print(f"Error loading datasets: {e}")
        return None, None, None

def analyze_statistics(df, dataset_name):
    """Calculates and prints general statistics for numeric columns."""
    print(f"\n{'='*20}")
    print(f"General Statistics for {dataset_name}")
    print(f"{'='*20}")
    
    # Select numeric columns
    numeric_df = df.select_dtypes(include=['int64', 'float64'])
    
    if numeric_df.empty:
        print("No numeric columns found.")
        return

    # Calculate statistics
    stats_df = numeric_df.agg(['mean', 'median'])
    print(stats_df.to_string())
    
    return stats_df

def analyze_pre_post(df, dataset_name):
    """Calculates statistics grouped by period (Pre vs Post Adoption)."""
    print(f"\n{'='*40}")
    print(f"Pre vs Post Adoption Analysis for {dataset_name}")
    print(f"{'='*40}")
    
    # Columns of interest
    target_cols = ['avg_complexity', 'median_complexity', 'avg_loc', 'median_loc', 'avg_nloc', 'files_changed_count']
    available_cols = [c for c in target_cols if c in df.columns]
    
    if not available_cols:
        print("Required columns for analysis not found.")
        return

    # Group by 'period' and calculate mean/median
    grouped_stats = df.groupby('period')[available_cols].agg(['mean', 'median'])
    print("\nGrouped Statistics (Mean & Median):")
    print(grouped_stats.to_string())

    # --- Significance Tests (Pre vs Post) ---
    print("\n--- Significance Tests (Pre vs Post) ---")
    
    try:
        pre_df = df[df['period'] == 'Pre-Adoption']
        post_df = df[df['period'] == 'Post-Adoption']
        
        for col in available_cols:
            print(f"\nAnalyzing {col}:")
            dist1 = pre_df[col].dropna()
            dist2 = post_df[col].dropna()
            
            if len(dist1) > 0 and len(dist2) > 0:
                mannUandCliffdelta(dist1.values, dist2.values)
            else:
                print("  Not enough data for test.")
    except Exception as e:
        print(f"Error comparing pre/post: {e}")

def main():
    # Set pandas display options to ensure all columns are shown
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    # Load Datasets
    agents_df, claude_df, copilot_df = load_data()
    
    if agents_df is None:
        return

    # Filter out commits with files_changed_count == 0 and avg_complexity == 0
    agents_df = agents_df[(agents_df['files_changed_count'] != 0) & (agents_df['avg_complexity'] != 0)]
    claude_df = claude_df[(claude_df['files_changed_count'] != 0) & (claude_df['avg_complexity'] != 0)]
    copilot_df = copilot_df[(copilot_df['files_changed_count'] != 0) & (copilot_df['avg_complexity'] != 0)]

    # --- Part 1: General Statistics ---
    analyze_statistics(agents_df, "Agents Adoption")
    analyze_pre_post(agents_df, "Agents Adoption")
    
    analyze_statistics(claude_df, "Claude Adoption")
    analyze_pre_post(claude_df, "Claude Adoption")
    
    analyze_statistics(copilot_df, "Copilot Adoption")
    analyze_pre_post(copilot_df, "Copilot Adoption")

    # --- Part 2: Significance Tests ---
    print("\n" + "=" * 40)
    print("           Significance Testing")
    print("=" * 40)

    # Prepare data for comparison
    agents_df['Dataset'] = 'Agents'
    claude_df['Dataset'] = 'Claude'
    copilot_df['Dataset'] = 'Copilot'
    
    combined_df = pd.concat([agents_df, claude_df, copilot_df], ignore_index=True)

    # Aggregate to repo-level to avoid duplicated per-repo ratio values
    repo_group = ['repository_owner', 'repository_name', 'Dataset']
    repo_level = (
        combined_df.groupby(repo_group)
        .mean(numeric_only=True)
        .reset_index()
    )

    # Identify numeric columns to compare (excluding the 'Dataset' identifier) on repo-level
    numeric_cols_to_compare = [
        col for col in repo_level.columns
        if repo_level[col].dtype in ['int64', 'float64'] and col != 'Dataset'
    ]

    # Get unique dataset names from repo-level data
    dataset_names = repo_level['Dataset'].unique()

    # Perform pairwise comparisons
    comparison_results = []

    for i in range(len(dataset_names)):
        for j in range(i + 1, len(dataset_names)):
            name1 = dataset_names[i]
            name2 = dataset_names[j]

            df1 = repo_level[repo_level['Dataset'] == name1]
            df2 = repo_level[repo_level['Dataset'] == name2]

            print(f"\nComparing {name1} vs {name2}")
            print("-" * 30)

            for col in numeric_cols_to_compare:
                print(f"  {col}:") # Print the variable name being tested

                data1 = df1[col]
                data2 = df2[col]

                # Prepare data: Remove NaNs *before* passing to the function
                data1_clean = data1.dropna()
                data2_clean = data2.dropna()

                try:
                    # Only perform test if both datasets have data for the column
                    if len(data1_clean) > 0 and len(data2_clean) > 0:

                            # Call provided function
                            u_stat, p_value, cliff_d, cliff_size = mannUandCliffdelta(
                                data1_clean.values, data2_clean.values
                            )

                            # Store results for the final DataFrame (report repo counts as N1/N2)
                            comparison_results.append({
                                'Dataset 1': name1,
                                'Dataset 2': name2,
                                'Variable': col,
                                'Mann-Whitney U Stat': round(u_stat, 2),
                                'P-value': f"{p_value:.6f}",
                                'N1': len(data1_clean),
                                'N2': len(data2_clean),
                                "Cliff's Delta (d)": round(cliff_d, 2),
                                "Cliff's Delta (size)": cliff_size
                            })
                    else:
                         print(f"    Not enough data for comparison")

                except ValueError as e:
                    # This catches errors, e.g., if all values are identical or other issues
                    print(f"    Error during calculation - {e}")
                except Exception as e:
                     # Catch any other unexpected errors
                     print(f"    An unexpected error occurred: {e}")

    # --- Display results in a DataFrame ---
    print("\n" + "=" * 40)
    print("           Final Comparison DataFrame")
    print("=" * 40)

    comparison_df = pd.DataFrame(comparison_results)
    print(comparison_df.to_string()) # Using to_string() for better terminal output than display()
    
    # Optional: Save to CSV
    # comparison_df.to_csv("adoption_significance_results.csv", index=False)

if __name__ == "__main__":
    main()
